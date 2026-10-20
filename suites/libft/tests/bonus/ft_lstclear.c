#include "libft_test.h"

static t_list	*mk(int n)
{
	t_list	*head = NULL;

	while (n > 0)
	{
		t_list	*node = malloc(sizeof(t_list));
		int		*v = malloc(sizeof(int));

		*v = n--;
		node->content = v;
		node->next = head;
		head = node;
	}
	return (head);
}

static void	free_list(t_list *l, int free_content)
{
	while (l)
	{
		t_list	*n = l->next;

		if (free_content)
			free(l->content);
		free(l);
		l = n;
	}
}

static int	g_deleted;

static void	del(void *p)
{
	g_deleted++;
	free(p);
}

DT_TEST(ft_lstclear, basic, "Deletes every node and sets the list to NULL (no leak)")
{
	t_list	*l = mk(4);

	g_deleted = 0;
	ft_lstclear(&l, del);
	DT_EXPECT_NULL(l);
	DT_EXPECT_EQ_INT(g_deleted, 4);
}

DT_TEST(ft_lstclear, empty, "Clearing an empty list does nothing")
{
	t_list	*l = NULL;

	ft_lstclear(&l, del);
	DT_EXPECT_NULL(l);
}
