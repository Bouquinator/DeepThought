#include "sstyle.h"
#include <stdlib.h>

DT_TEST(ft_lstadd_back, scenario, "ft_lstadd_back: every case in order (each case builds on the previous one)")
{
	t_list	*list;
	t_list	*n1;
	t_list	*n2;
	t_list	*n3;

	/* add to empty list (*lst is NULL): new node becomes the list */
	list = NULL;
	n1 = ft_lstnew((void *)(uintptr_t)10);
	ft_lstadd_back(&list, n1);
	DT_CHECK_PTR("lstadd_back on empty: head == n1", list, n1);
	DT_CHECK_PTR("lstadd_back on empty: n1->next == NULL", n1->next, NULL);

	/* add second: head unchanged, n2 appended at tail */
	n2 = ft_lstnew((void *)(uintptr_t)20);
	ft_lstadd_back(&list, n2);
	DT_CHECK_PTR("lstadd_back 2nd: head still n1", list, n1);
	DT_CHECK_PTR("lstadd_back 2nd: n1->next == n2", n1->next, n2);

	/* add third: must walk past the head to reach the tail */
	n3 = ft_lstnew((void *)(uintptr_t)30);
	ft_lstadd_back(&list, n3);
	DT_CHECK_PTR("lstadd_back 3rd: head still n1", list, n1);
	DT_CHECK_PTR("lstadd_back 3rd: n1->next == n2", n1->next, n2);
	DT_CHECK_PTR("lstadd_back 3rd: n2->next == n3", n2->next, n3);
	DT_CHECK_PTR("lstadd_back 3rd: n3->next == NULL", n3->next, NULL);

	free(n1);
	free(n2);
	free(n3);
}
