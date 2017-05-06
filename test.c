#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
        for (int i = 0; i < 3; ++i) {
                sleep(1);
                printf("%i\n", i);
        }
}
