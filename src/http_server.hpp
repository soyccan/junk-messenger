#ifndef _HTTP_SERVER_HPP_
#define _HTTP_SERVER_HPP_

#include <arpa/inet.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <netinet/ip.h>
#include <poll.h>
#include <pthread.h>
#include <semaphore.h>
#include <signal.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <sys/types.h>

#include <assert.h>
#include <stdlib.h>
#include <string>

#include "debug.h"
#include "http_request.hpp"


static inline int sock_set_non_blocking(int fd)
{
    int flags = fcntl(fd, F_GETFL, 0);
    if (flags == -1) {
        log_err("fcntl");
        return -1;
    }

    flags |= O_NONBLOCK;
    int s = fcntl(fd, F_SETFL, flags);
    if (s == -1) {
        log_err("fcntl");
        return -1;
    }
    return 0;
}

struct HTTPServer {
    int listen_fd;
    pthread_t listen_thread;

    bool to_shutdown;
    sem_t is_shutdown;

    std::list<HTTPRequest> request_list;
    std::list<HTTPRequest *> zombie_queue;
    pthread_mutex_t zombie_lock;
    pthread_cond_t zombie_cond;

    HTTPServer(in_port_t port = 80, std::string addr = "127.0.0.1")
        : to_shutdown(false)
    {
        log_info("Web server started");

#ifdef __MACH__  // macOS
        this->listen_fd = socket(PF_INET, SOCK_STREAM, 0);
#else
        this->listen_fd = socket(AF_INET, SOCK_STREAM, 0);
#endif

        struct sockaddr_in bind_addr;
        bind_addr.sin_family = AF_INET;
        bind_addr.sin_port = htons(port);
        bind_addr.sin_addr.s_addr = inet_addr(addr.c_str());

        // still bind socket if address is used
        int reuseaddr = 1;
        G(setsockopt(this->listen_fd, SOL_SOCKET, SO_REUSEADDR, &reuseaddr,
                     sizeof(int)));

        G(bind(this->listen_fd, (struct sockaddr *) &bind_addr,
               sizeof(bind_addr)));
        G(listen(this->listen_fd, SOMAXCONN));
        // G(sock_set_non_blocking(this->listen_fd));

        G(sem_init(&this->is_shutdown, 0, 0));
        G(pthread_mutex_init(&this->zombie_lock, NULL));
        G(pthread_cond_init(&this->zombie_cond, NULL));
    }

    static void *listen_thread_loop(void *self_)
    {
        HTTPServer *self = (HTTPServer *) self_;
        while (!self->to_shutdown) {
            self->accept_request();
        }
        // G(sem_post(&self->is_shutdown));
        return NULL;
    }

    void serve_forever()
    {
        int ret;
        ret = pthread_create(&this->listen_thread, NULL,
                             this->listen_thread_loop, this);
        if (ret < 0) {
            log_err("pthread_create");
            return;
        }

        while (!this->to_shutdown) {
            pthread_mutex_lock(&this->zombie_lock);
            while (this->zombie_queue.empty()) {
                pthread_cond_wait(&this->zombie_cond, &this->zombie_lock);
            }
            pthread_mutex_unlock(&this->zombie_lock);
        }

        G(pthread_join(this->listen_thread, NULL));
    }

    void shutdown()
    {
        this->to_shutdown = true;

        log_info("Waiting thread to terminate");
        pthread_kill(this->listen_thread, SIGINT);
        // G(sem_wait(&this->is_shutdown));

        log_info("Closing socket");
        G(::shutdown(this->listen_fd, SHUT_RDWR));
    }

    /* Called after select() so that this is nonblocking
     * Return: 0 if there is no more connection
     *         1 if a connection is successfully accepted
     *         -1 on error
     */
    int accept_request()
    {
        struct sockaddr_in in_addr = {0};
        socklen_t in_addr_len = 0;

        int in_fd =
            accept(this->listen_fd, (struct sockaddr *) &in_addr, &in_addr_len);

        if (in_fd < 0) {
            if (errno == EAGAIN || errno == EWOULDBLOCK) {
                // no more incoming connection
                return 0;
            } else {
                log_err("accept");
                return -1;
            }
        }

        log_info("accepted fd=%d addr=%s port=%d", in_fd,
                 inet_ntoa(in_addr.sin_addr), in_addr.sin_port);

        // TODO: non-blockng IO
        // G(sock_set_non_blocking(in_fd));

        this->request_list.emplace_back(in_fd, &this->zombie_queue,
                                        &this->zombie_lock, &this->zombie_cond);
        auto &request = this->request_list.back();
        request.handle();

        return 1;
    }

    // void close_request(int fd)
    // {
    //     for (auto r = this->request_list.begin(); r !=
    //     this->request_list.end();
    //          r++) {
    //         if (r->client_fd == fd) {
    //             this->request_list.erase(r);
    //             break;
    //         }
    //     }
    // }
    //
    // int handle_request_noblock(int fd)
    // {
    //     for (HTTPRequest &r : this->request_list) {
    //         if (r.client_fd == fd) {
    //             r.handle();
    //             break;
    //         }
    //     }
    //     return 0;
    // }
};

#endif
