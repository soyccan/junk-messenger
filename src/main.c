#include <arpa/inet.h>
#include <netinet/in.h>
#include <netinet/ip.h>
#include <poll.h>
#include <signal.h>
#include <sys/socket.h>
#include <sys/types.h>

#include <assert.h>
#include <stdio.h>

#include "logging.h"

int main()
{
    /* when a fd is closed by remote, writing to this fd will cause system
     * send SIGPIPE to this process, which exit the program
     */
    if (sigaction(SIGPIPE,
                  &(struct sigaction){.sa_handler = SIG_IGN, .sa_flags = 0},
                  NULL)) {
        log_err("Failed to install signal handler for SIGPIPE");
        return 0;
    }

    int ret = 0;
    int listen_fd = open_listen_socket(PORT);

    log_info("Web server started");


    return 0;
}
