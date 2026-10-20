#include "sstyle.h"
#include <stdlib.h>

static int	g_del_count;

static void	del_noop(void *content)
{
	(void)content;
	g_del_count++;
}

static void	*map_add1(void *content)
{
	return ((void *)((uintptr_t)content + 1));
}

static void	*map_double(void *content)
{
	return ((void *)((uintptr_t)content * 2));
}

DT_TEST(ft_lstmap, scenario, "ft_lstmap: every case in order (each case builds on the previous one)")
{
	t_list	*n1;
	t_list	*n2;
	t_list	*n3;
	t_list	*src;
	t_list	*mapped;

	/* NULL lst → NULL */
	mapped = ft_lstmap(NULL, map_add1, del_noop);
	DT_CHECK_PTR("lstmap(NULL, f, del) == NULL", mapped, NULL);

	/* NULL f → NULL */
	n1 = ft_lstnew((void *)(uintptr_t)1);
	mapped = ft_lstmap(n1, NULL, del_noop);
	DT_CHECK_PTR("lstmap(lst, NULL, del) == NULL", mapped, NULL);
	free(n1);

	/* NULL del → NULL */
	n1 = ft_lstnew((void *)(uintptr_t)1);
	mapped = ft_lstmap(n1, map_add1, NULL);
	DT_CHECK_PTR("lstmap(lst, f, NULL) == NULL", mapped, NULL);
	free(n1);

	/* three-node mapping: 1→2→3 doubled to 2→4→6 */
	n1 = ft_lstnew((void *)(uintptr_t)1);
	n2 = ft_lstnew((void *)(uintptr_t)2);
	n3 = ft_lstnew((void *)(uintptr_t)3);
	n1->next = n2;
	n2->next = n3;
	n3->next = NULL;
	src = n1;
	g_del_count = 0;
	mapped = ft_lstmap(src, map_double, del_noop);
	DT_CHECK_NOT_NULL("lstmap([1,2,3], *2): result not NULL", mapped);
	if (mapped)
	{
		DT_CHECK_UINT("lstmap([1,2,3], *2): size == 3", ft_lstsize(mapped), 3);
		DT_CHECK_PTR("lstmap: [0].content == 2", mapped->content, (void *)(uintptr_t)2);
		if (mapped->next)
			DT_CHECK_PTR("lstmap: [1].content == 4", mapped->next->content, (void *)(uintptr_t)4);
		if (mapped->next && mapped->next->next)
		{
			DT_CHECK_PTR("lstmap: [2].content == 6",
				mapped->next->next->content, (void *)(uintptr_t)6);
			DT_CHECK_PTR("lstmap: [2].next == NULL", mapped->next->next->next, NULL);
		}
		/* result nodes must be distinct from source nodes */
		if (!(mapped != src))
		{
			DT_FAILF("lstmap: result == src (same pointer!)");
		}
		ft_lstclear(&mapped, del_noop);
	}
	/* original list must be fully intact after mapping */
	DT_CHECK_PTR("lstmap: original [0].content == 1", n1->content, (void *)(uintptr_t)1);
	DT_CHECK_PTR("lstmap: original [1].content == 2", n2->content, (void *)(uintptr_t)2);
	DT_CHECK_PTR("lstmap: original [2].content == 3", n3->content, (void *)(uintptr_t)3);
	DT_CHECK_PTR("lstmap: original n1->next == n2", n1->next, n2);
	DT_CHECK_PTR("lstmap: original n2->next == n3", n2->next, n3);
	DT_CHECK_PTR("lstmap: original n3->next == NULL", n3->next, NULL);
	free(n1);
	free(n2);
	free(n3);
}
