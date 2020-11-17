#ifndef _HTTP_SERVER_HPP_
#define _HTTP_SERVER_HPP_

#include <arpa/inet.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <netinet/ip.h>
#include <poll.h>
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
    std::list<HTTPRequest> request_list;

    const static size_t NUM_POLL_FD = 1024;
    fd_set poll_fds;

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
        G(sock_set_non_blocking(this->listen_fd));

        FD_ZERO(&this->poll_fds);
        FD_SET(this->listen_fd, &this->poll_fds);
    }

    ~HTTPServer()
    {
        log_info("closing socket");
        G(::shutdown(this->listen_fd, SHUT_RDWR));
    }

    void serve_forever()
    {
        while (!this->to_shutdown) {
            log_debug("select");

            fd_set fdr, fde;  // fdset for read and exception
            memcpy(&fdr, &this->poll_fds, sizeof(fdr));
            memcpy(&fde, &this->poll_fds, sizeof(fde));
            struct timeval t;
            t.tv_sec = 0;
            t.tv_usec = 500000;
            int n_ready = select(1024, &fdr, NULL, &fde, &t);

            // if (this->to_shutdown)
            //     break;

            for (int i = 0; i < 1024; i++) {
                if (FD_ISSET(i, &fde)) {
                    // socket is closed
                    // TODO: other exception than closed socket?
                    this->close_request(i);
                } else if (FD_ISSET(i, &fdr)) {
                    if (i == this->listen_fd) {
                        // one or more incoming connections
                        do {
                        } while (this->accept_request() > 0);
                    } else {
                        this->handle_request_noblock(i);
                    }
                }
            }
        }
    }

    void shutdown() { this->to_shutdown = true; }

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

        FD_SET(in_fd, &this->poll_fds);

        this->request_list.emplace_back(in_fd);
        return 1;
    }

    void close_request(int fd)
    {
        for (auto r = this->request_list.begin(); r != this->request_list.end();
             r++) {
            if (r->client_fd == fd) {
                FD_CLR(fd, &this->poll_fds);
                this->request_list.erase(r);
                break;
            }
        }
    }

    int handle_request_noblock(int fd)
    {
        for (HTTPRequest &r : this->request_list) {
            if (r.client_fd == fd) {
                r.handle();
                break;
            }
        }
        return 0;
    }
};

#endif
