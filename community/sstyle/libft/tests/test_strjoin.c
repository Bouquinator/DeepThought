#include "sstyle.h"
#include <stdlib.h>
#include <string.h>

DT_TEST(ft_strjoin, basic_join, "basic join")
{
	char	*r;

	r = ft_strjoin("Hello", " World");
	DT_CHECK_STR("strjoin(\"Hello\",\" World\")", r, "Hello World");
	free(r);
}

DT_TEST(ft_strjoin, empty_s1, "empty s1")
{
	char	*r;

	r = ft_strjoin("", "World");
	DT_CHECK_STR("strjoin(\"\",\"World\")", r, "World");
	free(r);
}

DT_TEST(ft_strjoin, empty_s2, "empty s2")
{
	char	*r;

	r = ft_strjoin("Hello", "");
	DT_CHECK_STR("strjoin(\"Hello\",\"\")", r, "Hello");
	free(r);
}

DT_TEST(ft_strjoin, both_empty, "both empty")
{
	char	*r;

	r = ft_strjoin("", "");
	DT_CHECK_STR("strjoin(\"\",\"\")", r, "");
	free(r);
}

DT_TEST(ft_strjoin, very_long_strings, "very long strings: 511 + 511 = 1022 chars")
{
	char	*r;

	{
		static char	long1[512];
		static char	long2[512];
		memset(long1, 'a', 511); long1[511] = '\0';
		memset(long2, 'b', 511); long2[511] = '\0';
		r = ft_strjoin(long1, long2);
		DT_CHECK_NOT_NULL("strjoin(511+'a', 511+'b') non-NULL", r);
		if (r)
		{
			DT_CHECK_SIZE("strjoin long: result length", strlen(r), 1022);
			free(r);
		}
	}
}

DT_TEST(ft_strjoin, null_inputs_to_null_return_without, "NULL inputs → NULL return without crash")
{
	char	*r;

	r = ft_strjoin(NULL, "x");
	if (!(r == NULL))
	{
		DT_FAILF("strjoin(NULL,\"x\") → expected NULL");
		free(r);
	}
	r = ft_strjoin("x", NULL);
	if (!(r == NULL))
	{
		DT_FAILF("strjoin(\"x\",NULL) → expected NULL");
		free(r);
	}
}
