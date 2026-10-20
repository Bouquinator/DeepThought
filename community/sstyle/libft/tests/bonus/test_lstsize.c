#include "sstyle.h"
#include <stdlib.h>

DT_TEST(ft_lstsize, scenario, "ft_lstsize: every case in order (each case builds on the previous one)")
{
	t_list	*n1;
	t_list	*n2;
	t_list	*n3;

	/* NULL → 0 */
	DT_CHECK_UINT("lstsize(NULL) == 0", ft_lstsize(NULL), 0);

	/* single node */
	n1 = ft_lstnew((void *)(uintptr_t)1);
	n1->next = NULL;
	DT_CHECK_UINT("lstsize([1]) == 1", ft_lstsize(n1), 1);

	/* three nodes */
	n2 = ft_lstnew((void *)(uintptr_t)2);
	n3 = ft_lstnew((void *)(uintptr_t)3);
	n1->next = n2;
	n2->next = n3;
	n3->next = NULL;
	DT_CHECK_UINT("lstsize([1,2,3]) == 3", ft_lstsize(n1), 3);

	free(n1);
	free(n2);
	free(n3);
}
