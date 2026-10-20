#include "sstyle.h"
#include <stdlib.h>
#include <string.h>

DT_TEST(ft_strdup, empty_string, "empty string")
{
	char	*r;

	r = ft_strdup("");
	DT_CHECK_STR("ft_strdup(\"\") content", r, "");
	free(r);
}

DT_TEST(ft_strdup, content_copied_and_result_must_be, "content copied and result must be a different pointer")
{
	char	*r;
	const char *src;

	src = "hello";
	r = ft_strdup(src);
	DT_CHECK_STR("ft_strdup(\"hello\") content", r, "hello");
	if (r)
	{
		if (!((void *)r != (void *)src))
		{
			DT_FAILF("ft_strdup: result == src (not a copy!)");
		}
		free(r);
	}
}

DT_TEST(ft_strdup, null_input_to_null_return_without, "NULL input → NULL return without crash")
{
	char	*r;

	r = ft_strdup(NULL);
	if (!(r == NULL))
	{
		DT_FAILF("ft_strdup(NULL) → expected NULL");
		free(r);
	}
}
