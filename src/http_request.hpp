#ifndef _HTTP_REQUEST_HPP_
#define _HTTP_REQUEST_HPP_

#include <stdint.h>
#include <unistd.h>

#define MAX_BUF_SIZE 1000

static inline bool streq16(const char *s, int x0, int x1)
{
    return *(uint16_t *) s == ((x1 << 8) | x0);
}

static inline char *parse_header_line(char **phdr, const char *end)
{
    char *pln = *phdr;
    while (*phdr < end && !streq16(*phdr, '\r', '\n'))
        (*phdr)++;
    *(*phdr - 1) = '\0';
    return pln;
}

struct HTTPRequest {
    int client_fd;
    char buf[MAX_BUF_SIZE];

    HTTPRequest(int client_fd) : client_fd(client_fd) {}

    void handle()
    {
        char *pbuf = buf;
        size_t sz_read = 0;
        while (1) {
            int ret =
                ::read(this->client_fd, buf + sz_read, MAX_BUF_SIZE - sz_read);
            if (ret < 0) {
                log_err("read");
                sz_read = 0;
            } else {
                sz_read = ret;
            }
            buf[MAX_BUF_SIZE - 1] = '\0';


            char *phdr = buf;
            char *p = phdr;
            while (p < buf + sz_read && !streq16(p, '\r', '\n'))
                p++;
            *p = '\0';
            phdr = p + 2;
        }
        this->close();
    }

    void close() { ::close(this->client_fd); }
};

#endif
