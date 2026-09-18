/*
 * 6_c_demo.c  —  Load this with the "Load C" button in the GUI
 * Shows: struct, malloc, global pointer, function call, field access
 */
#include <stdlib.h>

struct Node {
    struct Node* next;
    int val;
};

struct Node* g;

void alloc() {
    struct Node* t = (struct Node*)malloc(sizeof(struct Node));
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
