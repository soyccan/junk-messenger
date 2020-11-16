#ifndef _HTTP_SERVER_HPP_
#define _HTTP_SERVER_HPP_

#include <arpa/inet.h>
#include <netinet/in.h>
#include <netinet/ip.h>
#include <poll.h>
#include <sys/socket.h>
#include <sys/types.h>

#include <assert.h>
#include <stdlib.h>

#include "debug.h"
#include "http_server.h"


struct HTTPServer {
    int listen_fd;

    HTTPServer()
    {
#ifdef __MACH__  // macOS
        self->listen_fd = socket(PF_INET, SOCK_STREAM, 0);
#else
        self->listen_fd = socket(AF_INET, SOCK_STREAM, 0);
#endif

        G(listen(self->listen_fd, SOMAXCONN));
        G(sock_set_non_blocking(self->listen_fd));
    }

    void handle_request()
    {
        while (1) {
            struct pollfd poll_fds[] = {
                {.fd = self->listen_fd, .events = POLLIN, .revents = 0}};
            int n_ready = poll(poll_fds, 1, 0);
            assert(n_ready >= 0 && "poll");

            // if (poll_fds[0].revents & POLLIN) {
            if (n_ready > 0) {
                // one or more incoming connections
                do
                    ;
                while (self->handle_request_noblock(self) > 0);
            }
        }
    }

    /* Called after select() so that this is nonblocking
     * Return: 0 if there is no more connection
     *         1 if a connection is successfully accepted
     *         -1 on error
     */
    int handle_request_noblock()
    {
        struct sockaddr_in in_addr = {0};
        socklen_t in_addr_len = 0;

        int in_fd =
            accept(self->listen_fd, (struct sockaddr *) &in_addr, &in_addr_len);

        log_info("accepted fd=%d addr=%s port=%d", in_fd,
                 inet_ntoa(ntohl(addr.sin_addr.s_addr)), addr.sin_port);

        if (in_fd < 0) {
            if (errno == EAGAIN || errno == EWOULDBLOCK) {
                // no more incoming connection
                return 0;
            } else {
                log_err("accept");
                return -1;
            }
        }

        G(sock_set_non_blocking(in_fd));

        HTTPRequest request(in_fd);
        request.handle();
        return 1;
    }
};

#endif
