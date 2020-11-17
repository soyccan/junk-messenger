#ifndef _DEBUG_H_
#define _DEBUG_H_

#include "logging.h"

// guard system call error
#define G(expr)         \
    if ((expr) < 0) {   \
        log_err(#expr); \
    }

#endif
