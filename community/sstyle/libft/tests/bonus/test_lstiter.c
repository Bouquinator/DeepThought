#include "sstyle.h"
#include <stdlib.h>

static int			g_iter_count;
static uintptr_t	g_iter_vals[16];

static void	f_capture(void *content)
{
	if (g_iter_count < 16)
		g_iter_vals[g_iter_count] = (uintptr_t)content;
	g_iter_count++;
}

DT_TEST(ft_lstiter, scenario, "ft_lstiter: every case in order (each case builds on the previous one)")
{
	t_list	*n1;
	t_list	*n2;
	t_list	*n3;

	/* NULL list → f not called, no crash */
	g_iter_count = 0;
	ft_lstiter(NULL, f_capture);
	DT_CHECK_INT("lstiter(NULL): f not called", g_iter_count, 0);

	/* three nodes: f called 3 times in FIFO order 1→2→3 */
	g_iter_count = 0;
	n1 = ft_lstnew((void *)(uintptr_t)1);
	n2 = ft_lstnew((void *)(uintptr_t)2);
	n3 = ft_lstnew((void *)(uintptr_t)3);
	n1->next = n2;
	n2->next = n3;
	n3->next = NULL;
	ft_lstiter(n1, f_capture);
	DT_CHECK_INT("lstiter([1,2,3]): f called 3 times", g_iter_count, 3);
	if (g_iter_count >= 3)
	{
		DT_CHECK_PTR("lstiter: 1st arg == 1", (void *)g_iter_vals[0], (void *)(uintptr_t)1);
		DT_CHECK_PTR("lstiter: 2nd arg == 2", (void *)g_iter_vals[1], (void *)(uintptr_t)2);
		DT_CHECK_PTR("lstiter: 3rd arg == 3", (void *)g_iter_vals[2], (void *)(uintptr_t)3);
	}

	/* lstiter must not modify list structure */
	DT_CHECK_PTR("lstiter: n1->next unchanged", n1->next, n2);
	DT_CHECK_PTR("lstiter: n2->next unchanged", n2->next, n3);
	DT_CHECK_PTR("lstiter: n3->next == NULL", n3->next, NULL);

	free(n1);
	free(n2);
	free(n3);
}
