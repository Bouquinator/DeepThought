#include "libft_test.h"

static int	g_deleted;

static void	del(void *p)
{
	g_deleted++;
	free(p);
}

DT_TEST(ft_lstdelone, basic, "Frees the content with del and the node with free (no leak)")
{
	t_list	*n = malloc(sizeof(t_list));

	n->content = malloc(8);
	n->next = NULL;
	g_deleted = 0;
	ft_lstdelone(n, del);
	DT_EXPECT_EQ_INT(g_deleted, 1);
}
