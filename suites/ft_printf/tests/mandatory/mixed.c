#include "printf_test.h"

DT_TEST(mixed, plain_text, "No conversion: prints the format")
{
	CMP("Hello, 42!\n");
}

DT_TEST(mixed, empty_format, "Empty format: prints nothing, returns 0")
{
	CMP("");
}

DT_TEST(mixed, everything, "Every conversion in one call")
{
	int	x;

	CMP("%c|%s|%p|%d|%i|%u|%x|%X|%%\n", 'Z', "str", (void *)&x, -1, 2, 3u, 255, 255);
}

DT_TEST(mixed, many_args, "Twenty arguments")
{
	CMP("%d%d%d%d%d%d%d%d%d%d%d%d%d%d%d%d%d%d%d%d",
		1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20);
}

DT_TEST(mixed, newline_only, "Only newlines")
{
	CMP("\n\n\n");
}
