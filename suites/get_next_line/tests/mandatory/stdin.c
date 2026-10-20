#include "gnl_test.h"

static void	from_stdin(const char *name)
{
	int	fd = open(dt_fixture(name), O_RDONLY);

	dt_input("reading stdin (fd 0) filled with fixtures/%s, BUFFER_SIZE=%ld", name, (long)BUFFER_SIZE);
	dup2(fd, 0);
	close(fd);
	expect_lines(0, dt_fixture(name));
}

DT_TEST(stdin, multiple_lines, "Reads from stdin (fd 0)")
{
	from_stdin("multi.txt");
}

DT_TEST(stdin, no_final_newline, "stdin without a final newline")
{
	from_stdin("multi_no_nl.txt");
}

DT_TEST(stdin, pipe, "Reads from a pipe written in several chunks")
{
	int		p[2];
	char	*l;

	if (pipe(p) < 0)
		dt_skip("pipe() failed");
	dt_input("a pipe written in 3 chunks: \"first li\" + \"ne\\nsecond\\n\" + \"third\", BUFFER_SIZE=%ld",
		(long)BUFFER_SIZE);
	write(p[1], "first li", 8);
	write(p[1], "ne\nsecond\n", 10);
	write(p[1], "third", 5);
	close(p[1]);
	l = get_next_line(p[0]);
	DT_EXPECT_EQ_STR(l, "first line\n");
	free(l);
	l = get_next_line(p[0]);
	DT_EXPECT_EQ_STR(l, "second\n");
	free(l);
	l = get_next_line(p[0]);
	DT_EXPECT_EQ_STR(l, "third");
	free(l);
	l = get_next_line(p[0]);
	DT_EXPECT_NULL(l);
	free(l);
	close(p[0]);
}
