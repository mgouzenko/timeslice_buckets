#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
        for (int i = 0; i < 3; ++i) {
                int a = 0;
                for (int j = 0; j < 100; ++j)
                        a += rand();
                sleep(1);
                printf("%i\n", a);
        }
}
