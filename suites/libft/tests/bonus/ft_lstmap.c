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

static void	*plus_ten(void *p)
{
	int	*v = malloc(sizeof(int));

	if (v)
		*v = *(int *)p + 10;
	return (v);
}

static void	del(void *p)
{
	free(p);
}

DT_TEST(ft_lstmap, basic, "Builds a new list with f applied, original untouched")
{
	t_list	*l = mk(3);
	t_list	*m = ft_lstmap(l, plus_ten, del);

	DT_ASSERT_NOT_NULL(m);
	DT_EXPECT_EQ_INT(ft_lstsize(m), 3);
	DT_EXPECT_EQ_INT(*(int *)m->content, 11);
	DT_EXPECT_EQ_INT(*(int *)m->next->next->content, 13);
	DT_EXPECT_EQ_INT(*(int *)l->content, 1);
	free_list(l, 1);
	free_list(m, 1);
}

DT_TEST(ft_lstmap, malloc_fail, "A node allocation fails: returns NULL and frees everything (no leak)")
{
	t_list	*l = mk(3);

	dt_malloc_fail_at(4);
	DT_EXPECT_NULL(ft_lstmap(l, plus_ten, del));
	dt_malloc_reset();
	free_list(l, 1);
}
