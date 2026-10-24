#include "gnl_test.h"

DT_TEST(errors, negative_fd, "fd = -1 returns NULL")
{
	char	*l;

	dt_input("get_next_line(-1)");
	l = get_next_line(-1);

	DT_EXPECT_NULL(l);
	free(l);
}

DT_TEST(errors, closed_fd, "A closed fd returns NULL")
{
	char	*l;

	dt_input("get_next_line(42), fd 42 is not open");
	l = get_next_line(42);

	DT_EXPECT_NULL(l);
	free(l);
}

DT_TEST(errors, huge_fd, "fd above OPEN_MAX returns NULL without crashing")
{
	char	*l;

	dt_input("get_next_line(100000)");
	l = get_next_line(100000);

	DT_EXPECT_NULL(l);
	free(l);
}

DT_TEST(errors, read_error, "read() fails (a directory): returns NULL")
{
	int		fd = open(".", O_RDONLY);
	char	*l;

	dt_input("an fd opened on a directory: read() fails with EISDIR");
	l = get_next_line(fd);

	DT_EXPECT_NULL(l);
	free(l);
	close(fd);
}

DT_TEST(errors, read_error_midway, "A read error discards what was buffered: the next file starts clean")
{
	int		fd = open_fixture("multi.txt");
	char	*l;
	int		guard = 0;

	dt_input("read 1 line of fixtures/multi.txt, close the fd, call again (read error), then read another file on the same fd");
	free(get_next_line(fd));
	close(fd);
	/* lines already buffered may still come out; then read() fails -> NULL */
	while ((l = get_next_line(fd)) && guard++ < 100)
		free(l);
	DT_EXPECT_NULL(l);
	free(l);
	fd = open_fixture("one_line_nl.txt");
	expect_lines(fd, dt_fixture("one_line_nl.txt"));
	close(fd);
}

DT_TEST(errors, malloc_fail, "Every malloc fails: returns NULL without crashing")
{
	int		fd = open_fixture("multi.txt");
	char	*l;

	dt_input("fixtures/multi.txt while every malloc fails");
	dt_malloc_fail_all();
	l = get_next_line(fd);
	dt_malloc_reset();
	DT_EXPECT_NULL(l);
	free(l);
	close(fd);
	dt_leaks_ignore();
}
