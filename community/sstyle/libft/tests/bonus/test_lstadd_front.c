#include "sstyle.h"
#include <stdlib.h>

DT_TEST(ft_lstadd_front, scenario, "ft_lstadd_front: every case in order (each case builds on the previous one)")
{
	t_list	*list;
	t_list	*n1;
	t_list	*n2;

	/* add to empty list: new node becomes head, its stale next is reset */
	list = NULL;
	n1 = ft_lstnew((void *)(uintptr_t)10);
	n1->next = (t_list *)(uintptr_t)0xBAD;
	ft_lstadd_front(&list, n1);
	DT_CHECK_PTR("lstadd_front on empty: head == n1", list, n1);
	DT_CHECK_PTR("lstadd_front on empty: pre-set next overwritten to NULL", n1->next, NULL);

	/* add second node: new head, old head becomes n->next */
	n2 = ft_lstnew((void *)(uintptr_t)20);
	ft_lstadd_front(&list, n2);
	DT_CHECK_PTR("lstadd_front 2nd: head == n2", list, n2);
	DT_CHECK_PTR("lstadd_front 2nd: n2->next == n1", n2->next, n1);
	DT_CHECK_PTR("lstadd_front 2nd: n1->next == NULL", n1->next, NULL);

	free(n1);
	free(n2);
}
