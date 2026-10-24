#include "gnl_test.h"

DT_TEST(files, empty, "An empty file: the first call returns NULL")
{
	expect_file("empty.txt");
}

DT_TEST(files, one_line_nl, "One line ending with \\n")
{
	expect_file("one_line_nl.txt");
}

DT_TEST(files, one_line_no_nl, "One line without a final \\n")
{
	expect_file("one_line_no_nl.txt");
}

DT_TEST(files, only_newlines, "A file containing only newlines")
{
	expect_file("only_nl.txt");
}

DT_TEST(files, one_char, "A single character, no newline")
{
	expect_file("one_char.txt");
}

DT_TEST(files, multiple_lines, "Several lines of different lengths")
{
	expect_file("multi.txt");
}

DT_TEST(files, multiple_no_final_nl, "Several lines, the last one without \\n")
{
	expect_file("multi_no_nl.txt");
}

DT_TEST(files, long_line, "A 10000 character line followed by short ones")
{
	expect_file("long_line.txt");
}

DT_TEST(files, big_file, "A ~60 KB text file")
{
	expect_file("big.txt");
}

DT_TEST(files, no_leak_after_eof, "Reading to EOF frees everything (no leak)")
{
	expect_file("multi.txt");
}

DT_TEST(files, after_eof_again, "Calling again after EOF keeps returning NULL")
{
	int		fd = open_fixture("one_line_nl.txt");
	char	*l;

	dt_input("fixtures/one_line_nl.txt read to the end, then get_next_line called twice more");
	free(get_next_line(fd));
	l = get_next_line(fd);
	DT_EXPECT_NULL(l);
	free(l);
	l = get_next_line(fd);
	DT_EXPECT_NULL(l);
	free(l);
	close(fd);
}
