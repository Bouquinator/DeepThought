#include "sstyle.h"
#include <string.h>

static void	t_putendl(const char *label, const char *s,
	const char *expected)
{
	int		pfd[2];
	char	buf[256];
	int		n;

	if (pipe(pfd) < 0)
	{
		DT_FAILF("check failed");
		return ;
	}
	ft_putendl_fd((char *)s, pfd[1]);
	close(pfd[1]);
	n = (int)read(pfd[0], buf, (int)sizeof(buf) - 1);
	buf[n < 0 ? 0 : n] = '\0';
	close(pfd[0]);
	DT_CHECK_STR(label, buf, expected);
}

DT_TEST(ft_putendl_fd, basic_should_append_n, "basic — should append '\\n'")
{
	t_putendl("putendl_fd \"hello\"", "hello", "hello\n");
}

DT_TEST(ft_putendl_fd, empty_string_should_still_write_n, "empty string — should still write '\\n'")
{
	t_putendl("putendl_fd \"\"", "", "\n");
}

DT_TEST(ft_putendl_fd, string_already_ending_with_newline_gets, "string already ending with newline — gets a second '\\n'")
{
	t_putendl("putendl_fd \"hi\\n\"", "hi\n", "hi\n\n");
}
