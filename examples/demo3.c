/*
 * demo3.c  —  Linked List Traversal
 * Shows field-sensitive pointer analysis on struct->next chain.
 * Run: python c_to_ir.py examples/demo3.c
 */
#include <stdlib.h>

struct Node {
    struct Node* next;
    int val;
};

int main() {
    struct Node* head;
    struct Node* p;
    struct Node* q;
    head = (struct Node*)malloc(sizeof(struct Node));
    p    = (struct Node*)malloc(sizeof(struct Node));
    head->next = p;
    q = head->next;
    return 0;
}
