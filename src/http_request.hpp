#ifndef _HTTP_REQUEST_HPP_
#define _HTTP_REQUEST_HPP_

#include <assert.h>
#include <stdint.h>
#include <stdio.h>

#include <sys/socket.h>
#include <unistd.h>

#include <algorithm>
#include <list>
#include <memory>

#include "debug.h"
#include "logging.h"

static inline bool streq16(const char *s, unsigned char x0, unsigned char x1)
{
    return *(uint16_t *) s == (((uint16_t) x1 << 8) | ((uint16_t) x0));
}

static inline bool streq32(const char *s,
                           unsigned char x0,
                           unsigned char x1,
                           unsigned char x2,
                           unsigned char x3)
{
    return *(uint32_t *) s == (((uint32_t) x3 << 24) | ((uint32_t) x2 << 16) |
                               ((uint32_t) x1 << 8) | ((uint32_t) x0));
}

static inline char *parse_header_line(char **hdr, const char *hdrend)
{
    char *line = *hdr;
    char *_hdr = *hdr;
    while (_hdr < hdrend && !streq16(_hdr, '\r', '\n'))
        _hdr++;
    *_hdr = '\0';
    *hdr = _hdr + 2;
    return line;
}

struct HTTPRequest {
    const static size_t MAX_BUF_SIZE = 8192;          // 8KiB
    const static size_t MAX_REQUEST_LINE_LEN = 8192;  // 8KiB

    FILE *client_read, *client_write;
    int client_fd;
    bool to_close_conn;

    // ring buffer
    char buf[MAX_BUF_SIZE];
    // size_t write_pos, read_pos;

    // request line
    int http_major, http_minor;
    char method[8];
    std::string query_str;

    // headers
    // struct HTTPRequestHeader {
    //     void *key_start, *key_end;
    //     void *value_start, *value_end;
    // };
    // std::list<HTTPRequestHeader> header_list;

    HTTPRequest(int client_fd, bool file_stream = true)
        : client_fd(client_fd),
          to_close_conn(false),
          http_major(0),
          http_minor(0)
    {
        if (file_stream) {
            this->client_read = fdopen(client_fd, "rb");
            this->client_write = fdopen(client_fd, "wb");
            if (!this->client_read) {
                log_err("fdopen(r)");
            }
            if (!this->client_write) {
                log_err("fdopen(w)");
            }
        } else {
            this->client_read = NULL;
            this->client_write = NULL;
        }
    }

    ~HTTPRequest() { this->terminate(); }

    void handle()
    {
        this->to_close_conn = true;
        this->handle_one_request();

        // if Keep-Alive is received
        // while (!this->to_close_conn)
        //     this->handle_one_request();

        this->terminate();
    }

    void close_conn()
    {
        if (client_fd < 0)
            return;

        log_info("Closing connection fd=%d", client_fd);

        // TODO: shutdown vs. close
        // G(shutdown(this->client_fd, SHUT_RDWR));
        G(close(this->client_fd));

        // TODO: fclose after close?
        if (this->client_read)
            G(fclose(this->client_read));
        if (this->client_write)
            G(fclose(this->client_write));
        this->client_fd = -1;
        this->client_read = NULL;
        this->client_write = NULL;
    }

    void terminate() { this->close_conn(); }

    void handle_one_request()
    {
        log_debug("handle_one_request");

        int ret;
        ret = this->parse_request_line();
        if (ret == EINVAL) {
            // Bad Request
            this->response_error(400);
            return;
        } else if (ret != 0) {
            this->to_close_conn = true;
            return;
        }

        ret = this->parse_request_header();
        if (ret == EINVAL) {
            // Bad Request
            this->response_error(400);
            return;
        } else if (ret != 0) {
            this->to_close_conn = true;
            return;
        }

        this->do_request();
    }

    int parse_request_line()
    {
        // TODO: what if MAX_REQUEST_LINE_LEN is reached
        if (fgets(this->buf, MAX_BUF_SIZE, this->client_read) == NULL) {
            log_err("fgets");
            return errno;
        }

        char *reqline = this->buf;
        log_debug("Request: %s", reqline);

        char *method = strsep(&reqline, " ");
        if (!reqline)
            return EINVAL;
        char *query_str = strsep(&reqline, " ");
        if (!reqline)
            return EINVAL;
        char *http_version = strsep(&reqline, "\r\n");

        if (!reqline || !streq32(http_version, 'H', 'T', 'T', 'P') ||
            http_version[4] != '/' || http_version[6] != '.') {
            return EINVAL;
        }

        this->http_major = http_version[5] - '0';
        this->http_minor = http_version[7] - '0';
        strncpy(this->method, method, sizeof(this->method));
        this->query_str = query_str;

        log_debug("http=%d.%d method=%s querystr=%s", this->http_major,
                  this->http_minor, this->method, this->query_str.c_str());

        return 0;
    }

    int parse_request_header()
    {
        for (;;) {
            // TODO: what if MAX_REQUEST_LINE_LEN is reached
            if (fgets(this->buf, MAX_BUF_SIZE, this->client_read) == NULL) {
                log_err("fgets");
                if (feof(this->client_read))
                    return EINVAL;
                else
                    return errno;
            }

            char *hdr = this->buf;
            log_debug("header line: %s", hdr);

            if (hdr[0] == '\n' || (hdr[0] == '\r' && hdr[1] == '\n'))
                break;

            char *key = strsep(&hdr, ":");
            if (!hdr)
                return EINVAL;
            hdr++;
            char *value = strsep(&hdr, "\r\n");
            if (!hdr)
                return EINVAL;

            log_debug("Header field (%s) = (%s)", key, value);

            if (strcasecmp(key, "connection") == 0 &&
                strcasecmp(value, "keep-alive") == 0) {
                log_debug("keep-alive");
                this->to_close_conn = false;
            }
        }

        return 0;
    }

    void do_request()
    {
        if (strcmp(this->method, "GET") == 0)
            this->do_GET();
    }

    void do_GET()
    {
        if (query_str[0] == '/') {
            FILE *obj = fopen(this->query_str.c_str() + 1, "r");

            log_debug("filename=%s", this->query_str.c_str() + 1);

            if (!obj) {
                log_err("File not found");
                this->response_error(404);
            } else {
                size_t cont_len = 0;
                char *cont = NULL;

                fseek(obj, 0, SEEK_END);
                long sz = ftell(obj);

                log_debug("filesize=%ld filename=%s", sz,
                          this->query_str.c_str() + 1);

                cont = new char[sz];

                fseek(obj, 0, SEEK_SET);
                fread(cont, 1, sz, obj);
                cont_len = sz;

                fclose(obj);

                this->response(200, cont, cont_len);

                if (cont)
                    delete[] cont;
            }
        } else {
            this->response_error(404);
        }
    }

    void response(int status_code, const char *content, size_t content_len = 0)
    {
        if (!content)
            return;

        if (content_len == 0) {
            content_len = strlen(content);
        }

        log_debug("response status=%d cont=%s len=%d", status_code, content,
                  content_len);

        fprintf(this->client_write, "HTTP/1.0 ");
        fprintf(this->client_write,
                (status_code == 200
                     ? "200 OK"
                     : status_code == 404 ? "404 Not Found"
                                          : "500 Internal Server Error"));
        fprintf(this->client_write, "\r\n");
        fprintf(this->client_write, "Content-Length: %lu\r\n", content_len);
        fprintf(this->client_write, "Connection: Close\r\n");
        fprintf(this->client_write, "\r\n");
        fwrite(content, 1, content_len, this->client_write);
        G(fflush(this->client_write));
    }

    void response_error(int status_code)
    {
        this->response(status_code,
                       "<!DOCTYPE html>\n"
                       "<h1>404 Not Found!</h1>");
    }
};

#endif
