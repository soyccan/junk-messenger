#ifndef _LOGGER_H_
#define _LOGGER_H_

#include <errno.h>
#include <stdio.h>
#include <string.h>

#define LOG_COLOR_BEGIN_RED "\e[30m;"
#define LOG_COLOR_CLEAR "\e[0m;"
#define LOG_COLOR_RED(msg) (LOG_COLOR_BEGIN_RED msg LOG_COLOR_CLEAR)

#ifndef NDEBUG
#define log_debug(fmt, ...)                                         \
    fprintf(stderr, "[DEBUG] %s:%d: " fmt "\n", __FILE__, __LINE__, \
            ##__VA_ARGS__)
#else
#define log_debug(...)
#endif

#define log_err(fmt, ...)                                                \
    fprintf(stderr, "[ERROR] %s:%d (%s): " fmt "\n", __FILE__, __LINE__, \
            errno == 0 ? "0" : strerror(errno))

#define log_info(fmt, ...)                                     \
    printf("[INFO] %s:%d (%s): " fmt "\n", __FILE__, __LINE__, \
           errno == 0 ? "0" : strerror(errno))


#endif
