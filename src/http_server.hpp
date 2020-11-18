#ifndef _HTTP_SERVER_HPP_
#define _HTTP_SERVER_HPP_

#include <arpa/inet.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <netinet/ip.h>
#include <sys/epoll.h>
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
    bool to_shutdown;

    int epoll_fd;

    HTTPServer(in_port_t port = 80, std::string addr = "127.0.0.1")
        : to_shutdown(false)
    {
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
        G(sock_set_non_blocking(this->listen_fd));


        // epoll
        G(this->epoll_fd = epoll_create1(0));

        // this is not a real request, just for placed in epoll event list
        HTTPRequest *dummy = new HTTPRequest(this->listen_fd, false);
        struct epoll_event ev;
        ev.data.ptr = dummy;
        ev.events = EPOLLIN | EPOLLET;
        G(epoll_ctl(this->epoll_fd, EPOLL_CTL_ADD, this->listen_fd, &ev));


        log_info("Web server started");
    }

    void serve_forever()
    {
        const static size_t MAX_EVENT = 1024;
        struct epoll_event events[MAX_EVENT] = {};

        while (!this->to_shutdown) {
            log_debug("epoll");

            int n_event = epoll_wait(this->epoll_fd, events, MAX_EVENT, -1);

            if (n_event < 0) {
                log_err("epoll_wait");
                continue;
            }

            for (struct epoll_event *ev = events; ev < events + n_event; ev++) {
                HTTPRequest *rq = (HTTPRequest *) ev->data.ptr;
                if (rq->client_fd == this->listen_fd) {
                    // listening socket has events
                    if (ev->events & EPOLLIN) {
                        do
                            ;
                        while (this->accept_request() > 0);
                    } else {
                        log_info("listening fd has unknown event: %d",
                                 ev->events);
                    }
                } else {
                    // client socket has events
                    if ((ev->events & EPOLLERR) || (ev->events & EPOLLHUP) ||
                        !(ev->events & EPOLLIN)) {
                        log_err("epoll error fd: %d", rq->client_fd);
                        G(epoll_ctl(this->epoll_fd, EPOLL_CTL_DEL,
                                    rq->client_fd, ev));
                        delete rq;
                    } else {
                        ((HTTPRequest *) ev->data.ptr)->handle();
                    }
                }
            }
        }
    }

    void shutdown()
    {
        this->to_shutdown = true;

        log_info("Waiting thread to terminate");
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
        struct sockaddr_in in_addr;
        socklen_t in_addr_len = sizeof(struct sockaddr_in);

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

        G(sock_set_non_blocking(in_fd));

        HTTPRequest *rq = new HTTPRequest(in_fd);
        struct epoll_event ev;
        ev.data.ptr = rq;
        ev.events = EPOLLIN | EPOLLET | EPOLLONESHOT;
        G(epoll_ctl(this->epoll_fd, EPOLL_CTL_ADD, in_fd, &ev));

        return 1;
    }
};

#endif
