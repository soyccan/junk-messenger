#ifndef _LOGGER_H_
#define _LOGGER_H_

#include <errno.h>
#include <stdio.h>
#include <string.h>

#define LOG_COLOR_BEGIN_red "\e[31m"
#define LOG_COLOR_BEGIN_green "\e[32m"
#define LOG_COLOR_BEGIN_yellow "\e[33m"
#define LOG_COLOR_BEGIN_blue "\e[34m"
#define LOG_COLOR_BEGIN_magenta "\e[35m"
#define LOG_COLOR_BEGIN_cyan "\e[36m"
#define LOG_COLOR_BEGIN_white "\e[37m"
#define LOG_COLOR_CLEAR "\e[0m"
#define LOG_COLOR(color, msg) LOG_COLOR_BEGIN_##color msg LOG_COLOR_CLEAR

#ifndef NDEBUG
#define log_debug(fmt, ...)                                                    \
    fprintf(stderr, LOG_COLOR(white, "[DEBUG]") " %s:%d: " fmt "\n", __FILE__, \
            __LINE__, ##__VA_ARGS__)
#else
#define log_debug(...)
#endif

#define log_err(fmt, ...)                                               \
    fprintf(stderr, LOG_COLOR(red, "[ERROR]") " %s:%d (%s): " fmt "\n", \
            __FILE__, __LINE__, errno == 0 ? "" : strerror(errno),      \
            ##__VA_ARGS__)

#define log_info(fmt, ...)                                                \
    fprintf(stderr, LOG_COLOR(yellow, "[INFO]") " %s:%d (%s): " fmt "\n", \
            __FILE__, __LINE__, errno == 0 ? "" : strerror(errno),        \
            ##__VA_ARGS__)


#endif
