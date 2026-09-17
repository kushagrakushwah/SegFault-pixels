/*
 * demo2.c  —  Interprocedural with Global Pointer
 * Demonstrates VASCO context-sensitivity:
 *   alloc() writes the heap node into global 'g'
 *   main() reads it back via 'g' after the call
 * Run: python c_to_ir.py examples/demo2.c
 */
#include <stdlib.h>

struct Node {
    struct Node* next;
    int val;
};

struct Node* g;

void alloc() {
    struct Node* t;
    t = (struct Node*)malloc(sizeof(struct Node));
    g = t;
}

int main() {
    struct Node* a;
    struct Node* b;
    alloc();
    a = g;
    b = a;
    return 0;
}
