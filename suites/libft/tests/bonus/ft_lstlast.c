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

DT_TEST(ft_lstlast, basic, "Returns the last node")
{
	t_list	*l = mk(3);

	DT_ASSERT_NOT_NULL(ft_lstlast(l));
	DT_EXPECT_EQ_INT(*(int *)ft_lstlast(l)->content, 3);
	free_list(l, 1);
}

DT_TEST(ft_lstlast, empty, "NULL list returns NULL")
{
	DT_EXPECT_NULL(ft_lstlast(NULL));
}
