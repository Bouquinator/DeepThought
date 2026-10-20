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

DT_TEST(ft_lstadd_front, basic, "The new node becomes the head")
{
	t_list	*l = mk(2);
	t_list	*n = malloc(sizeof(t_list));

	n->content = NULL;
	n->next = NULL;
	ft_lstadd_front(&l, n);
	DT_EXPECT_EQ_PTR(l, n);
	DT_ASSERT_NOT_NULL(n->next);
	DT_EXPECT_EQ_INT(*(int *)n->next->content, 1);
	l = n->next;
	free(n);
	free_list(l, 1);
}

DT_TEST(ft_lstadd_front, empty, "Adding to an empty list")
{
	t_list	*l = NULL;
	t_list	n = {NULL, NULL};

	ft_lstadd_front(&l, &n);
	DT_EXPECT_EQ_PTR(l, &n);
	DT_EXPECT_NULL(n.next);
}
