#include <arpa/inet.h>
#include <netinet/in.h>
#include <netinet/ip.h>
#include <poll.h>
#include <signal.h>
#include <sys/socket.h>
#include <sys/types.h>

#include <assert.h>
#include <stdio.h>

#include "http_request.hpp"
#include "http_server.hpp"
#include "logging.h"


#define ADDR "0.0.0.0"
#define PORT 8081

HTTPServer server(PORT, ADDR);

void on_sigint(int signo)
{
    server.shutdown();
}

int main()
{
    /* when a fd is closed by remote, writing to this fd will cause system
     * send SIGPIPE to this process, which exit the program
     */
    struct sigaction act = {0};
    act.sa_handler = SIG_IGN;
    if (sigaction(SIGPIPE, &act, NULL)) {
        log_err("Failed to install signal handler for SIGPIPE");
        return 0;
    }

    act.sa_handler = on_sigint;
    if (sigaction(SIGINT, &act, NULL)) {
        log_err("Failed to install signal handler for SIGINT");
        return 0;
    }

    server.serve_forever();

    return 0;
}
