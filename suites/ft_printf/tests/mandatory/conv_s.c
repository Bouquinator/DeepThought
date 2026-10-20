#include "printf_test.h"

DT_TEST(s, basic, "%s prints a string")
{
	CMP("%s", "hello");
	CMP("[%s]", "42 school");
}

DT_TEST(s, empty, "An empty string prints nothing")
{
	CMP("%s", "");
	CMP("[%s][%s]", "", "x");
}

DT_TEST(s, null, "%s with NULL behaves like printf on this system")
{
	char	*s = NULL;

	CMP("%s", s);
	CMP("[%s]", s);
}

DT_TEST(s, long_string, "A 3000 character string")
{
	char	buf[3001];

	memset(buf, 'k', 3000);
	buf[3000] = 0;
	CMP("%s", buf);
}

DT_TEST(s, several, "Several strings and text")
{
	CMP("%s %s %s!", "one", "two", "three");
}
