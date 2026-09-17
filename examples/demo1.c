/*
 * demo1.c  —  Simple Aliasing
 * Demonstrates basic pointer aliasing in C.
 * Run: python c_to_ir.py examples/demo1.c
 */
#include <stdlib.h>

int main() {
    int* p;
    int* q;
    int* r;
    int x;
    p = &x;
    q = p;
    r = q;
    return 0;
}
