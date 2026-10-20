#include "sstyle.h"
#include <stdlib.h>

DT_TEST(ft_lstnew, integer_as_pointer_content, "integer-as-pointer content")
{
	t_list	*n;

	n = ft_lstnew((void *)(uintptr_t)42);
	DT_CHECK_NOT_NULL("lstnew(42) not NULL", n);
	if (n)
	{
		DT_CHECK_PTR("lstnew(42) content == 42", n->content, (void *)(uintptr_t)42);
		DT_CHECK_PTR("lstnew(42) next == NULL", n->next, NULL);
		free(n);
	}
}

DT_TEST(ft_lstnew, null_content_must_still_allocate_the, "NULL content — must still allocate the node")
{
	t_list	*n;

	n = ft_lstnew(NULL);
	DT_CHECK_NOT_NULL("lstnew(NULL) not NULL", n);
	if (n)
	{
		DT_CHECK_PTR("lstnew(NULL) content == NULL", n->content, NULL);
		free(n);
	}
}

DT_TEST(ft_lstnew, pointer_to_string_content, "pointer-to-string content: stored verbatim, not copied")
{
	t_list	*n;

	{
		char	*s = "libft";

		n = ft_lstnew((void *)s);
		DT_CHECK_NOT_NULL("lstnew(\"libft\") not NULL", n);
		if (n)
		{
			DT_CHECK_PTR("lstnew(\"libft\") content == str ptr", n->content, (void *)s);
			free(n);
		}
	}
}
