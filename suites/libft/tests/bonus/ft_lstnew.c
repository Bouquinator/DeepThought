#include "libft_test.h"

DT_TEST(ft_lstnew, basic, "Creates a node with content and next = NULL")
{
	int		x = 42;
	t_list	*n = ft_lstnew(&x);

	DT_ASSERT_NOT_NULL(n);
	DT_EXPECT_EQ_PTR(n->content, &x);
	DT_EXPECT_NULL(n->next);
	free(n);
}

DT_TEST(ft_lstnew, null_content, "NULL content is allowed")
{
	t_list	*n = ft_lstnew(NULL);

	DT_ASSERT_NOT_NULL(n);
	DT_EXPECT_NULL(n->content);
	free(n);
}

DT_TEST(ft_lstnew, malloc_fail, "Returns NULL when malloc fails")
{
	dt_malloc_fail_at(1);
	DT_EXPECT_NULL(ft_lstnew("x"));
}
