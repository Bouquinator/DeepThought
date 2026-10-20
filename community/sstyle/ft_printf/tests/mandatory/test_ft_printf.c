#include "pf.h"
/* Plain text, empty formats and several conversions in one call. */

static void	long_format(void)
{
	static char	fmt[20001];
	int			i;

	i = 0;
	while (i < 20000)
	{
		fmt[i] = 'a' + (i % 26);
		if (i % 1000 == 999)
			fmt[i] = '\n';
		i++;
	}
	fmt[i] = '\0';
	memcpy(fmt + 5000, "%d", 2);
	memcpy(fmt + 10000, "%s", 2);
	memcpy(fmt + 15000, "%x", 2);
	PF_L("20000-char format with %d %s %x inside", fmt, -42, "mid",
		0xBEEFu);
}

DT_TEST(ft_printf, plain_text, "plain text")
{
	PF("");
	PF("hello world\n");
	PF("\x01\x7f\xc3\xa9t\xc3\xa9 utf-8");
}

DT_TEST(ft_printf, one_conversion_surrounded_by_text, "one conversion surrounded by text")
{
	PF("before %s after", "middle");
}

DT_TEST(ft_printf, every_mandatory_conversion_in_a_single, "every mandatory conversion in a single call")
{
	PF("c=%c s=%s p=%p d=%d i=%i u=%u x=%x X=%X %%",
		'z', "hello", (void *)g_pf_exp, INT_MIN, INT_MAX, UINT_MAX, 0xabcdefu,
		0xabcdefu);
}

DT_TEST(ft_printf, many_arguments, "many arguments: va_list must advance correctly")
{
	PF("%d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d",
		1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
		20);
}

DT_TEST(ft_printf, arguments_of_different_sizes_interleaved, "arguments of different sizes interleaved (pointer is 8 bytes)")
{
	PF("%p %d %p %c %p %s", (void *)-1, -1, (void *)0, 'q',
		(void *)0x42, "end");

	long_format();
}
	