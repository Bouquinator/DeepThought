#include "sstyle.h"
#include <stdlib.h>

static char	to_upper(unsigned int i, char c)
{
	(void)i;
	if (c >= 'a' && c <= 'z')
		return (c - 32);
	return (c);
}

/* Records the first and last index received by the callback */
static unsigned int	g_first_idx;
static unsigned int	g_last_idx;
static int			g_calls;

static char	record_idx(unsigned int i, char c)
{
	if (g_calls == 0)
		g_first_idx = i;
	g_last_idx = i;
	g_calls++;
	return (c);
}

DT_TEST(ft_strmapi, only_letters_should_change, "only letters should change")
{
	char		*r;

	r = ft_strmapi("abc123!!", to_upper);
	DT_CHECK_STR("strmapi(\"abc123!!\", to_upper)", r, "ABC123!!");
	free(r);
}

DT_TEST(ft_strmapi, empty_string, "empty string")
{
	char		*r;

	r = ft_strmapi("", to_upper);
	DT_CHECK_STR("strmapi(\"\", to_upper)", r, "");
	free(r);
}

DT_TEST(ft_strmapi, index_passed_to_callback, "index passed to callback: 0 .. strlen-1")
{
	char		*r;

	g_calls = 0;
	g_first_idx = 999;
	g_last_idx = 999;
	r = ft_strmapi("hello", record_idx);
	DT_CHECK_UINT("strmapi: first char index == 0", g_first_idx, 0);
	DT_CHECK_UINT("strmapi: last char index == 4 (strlen-1)", g_last_idx, 4);
	free(r);
}
