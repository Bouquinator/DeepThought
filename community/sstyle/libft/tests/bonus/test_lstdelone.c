#include "sstyle.h"
#include <stdlib.h>

static int		g_del_count;
static void		*g_del_content;

static void	del_capture(void *content)
{
	g_del_content = content;
	g_del_count++;
}

DT_TEST(ft_lstdelone, del_is_called_exactly_once_with, "del is called exactly once with the node's content")
{
	t_list	*n;

	g_del_count = 0;
	g_del_content = (void *)(uintptr_t)0xBAD;
	n = ft_lstnew((void *)(uintptr_t)42);
	if (n)
	{
		ft_lstdelone(n, del_capture);
		DT_CHECK_INT("lstdelone: del called exactly once", g_del_count, 1);
		DT_CHECK_PTR("lstdelone: del receives node's content",
			g_del_content, (void *)(uintptr_t)42);
	}
}

DT_TEST(ft_lstdelone, null_lst_to_no_crash_del, "NULL lst → no crash, del not called")
{
	g_del_count = 0;
	ft_lstdelone(NULL, del_capture);
	DT_CHECK_INT("lstdelone(NULL): del not called", g_del_count, 0);
}

DT_TEST(ft_lstdelone, null_del_to_no_crash, "NULL del → no crash")
{
	t_list	*n;

	n = ft_lstnew((void *)(uintptr_t)99);
	if (n)
	{
		ft_lstdelone(n, NULL);
		/*
		** Per this implementation, !del causes an early return without free.
		** We must free the node ourselves to avoid a leak.
		*/
		free(n);
	}
}
