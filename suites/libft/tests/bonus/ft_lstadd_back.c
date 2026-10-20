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

DT_TEST(ft_lstadd_back, basic, "Appends at the end")
{
	t_list	*l = mk(2);
	t_list	n = {NULL, NULL};

	ft_lstadd_back(&l, &n);
	DT_EXPECT_EQ_PTR(l->next->next, &n);
	l->next->next = NULL;
	free_list(l, 1);
}

DT_TEST(ft_lstadd_back, empty, "Appending to an empty list sets the head")
{
	t_list	*l = NULL;
	t_list	n = {NULL, NULL};

	ft_lstadd_back(&l, &n);
	DT_EXPECT_EQ_PTR(l, &n);
}
