#include "sstyle.h"
#include <stdlib.h>

DT_TEST(ft_lstlast, scenario, "ft_lstlast: every case in order (each case builds on the previous one)")
{
	t_list	*n1;
	t_list	*n2;
	t_list	*n3;

	/* NULL → NULL */
	DT_CHECK_PTR("lstlast(NULL) == NULL", ft_lstlast(NULL), NULL);

	/* single node is both head and tail */
	n1 = ft_lstnew((void *)(uintptr_t)1);
	n1->next = NULL;
	DT_CHECK_PTR("lstlast([1]) == n1", ft_lstlast(n1), n1);

	/* three nodes: last is n3 */
	n2 = ft_lstnew((void *)(uintptr_t)2);
	n3 = ft_lstnew((void *)(uintptr_t)3);
	n1->next = n2;
	n2->next = n3;
	n3->next = NULL;
	DT_CHECK_PTR("lstlast([1,2,3]) == n3", ft_lstlast(n1), n3);

	free(n1);
	free(n2);
	free(n3);
}
