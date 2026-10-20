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

static void	twice(void *p)
{
	*(int *)p *= 2;
}

DT_TEST(ft_lstiter, basic, "Applies f to every content")
{
	t_list	*l = mk(3);

	ft_lstiter(l, twice);
	DT_EXPECT_EQ_INT(*(int *)l->content, 2);
	DT_EXPECT_EQ_INT(*(int *)l->next->content, 4);
	DT_EXPECT_EQ_INT(*(int *)l->next->next->content, 6);
	free_list(l, 1);
}
