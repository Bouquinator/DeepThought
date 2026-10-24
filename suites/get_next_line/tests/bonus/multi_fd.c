#include "gnl_test.h"

static void	expect(int fd, const char *want)
{
	char	*l = get_next_line(fd);

	if (want)
		DT_EXPECT_EQ_STR(l, want);
	else
		DT_EXPECT_NULL(l);
	free(l);
}

DT_TEST(bonus, interleaved, "Alternating between three fds keeps each position")
{
	int	a = open_fixture("multi.txt");
	int	b = open_fixture("only_nl.txt");
	int	c = open_fixture("one_line_nl.txt");

	dt_input("3 fds read in turn: a=multi.txt, b=only_nl.txt, c=one_line_nl.txt");
	expect(a, "Hello world\n");
	expect(b, "\n");
	expect(c, "This file has exactly one line.\n");
	expect(a, "this is line two, a bit longer than the first one\n");
	expect(b, "\n");
	expect(c, NULL);
	expect(a, "3\n");
	close(a);
	close(b);
	close(c);
	dt_leaks_ignore();
}

DT_TEST(bonus, whole_files, "Each fd read to the end gives the right content, without leaks")
{
	int	a = open_fixture("multi.txt");
	int	b = open_fixture("long_line.txt");

	expect_lines(a, dt_fixture("multi.txt"));
	expect_lines(b, dt_fixture("long_line.txt"));
	close(a);
	close(b);
}

DT_TEST(bonus, invalid_between, "An invalid fd in between does not disturb the others")
{
	int	a = open_fixture("multi.txt");

	dt_input("multi.txt on fd a, with get_next_line(-1) and get_next_line(4242) in between");
	expect(a, "Hello world\n");
	expect(-1, NULL);
	expect(4242, NULL);
	expect(a, "this is line two, a bit longer than the first one\n");
	close(a);
	dt_leaks_ignore();
}
