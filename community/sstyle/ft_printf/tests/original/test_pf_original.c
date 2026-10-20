#include "pf.h"
/*
** Combinations the C standard leaves undefined (incomplete or unknown
** conversions, flags that do not apply to the specifier, NULL format...).
** The subject does not require any particular output for them, so these
** suites belong to the informational Printf_original category: they report
** how close you are to the host libc and never count as failures.
**
** original_conversions only uses the mandatory syntax (no flags/width);
** original_flags covers the flag cases. Every case is its own test (its own
** process): a crash only fails that case.
*/

static void	format_alone(const char *fmt)
{
	char	label[64];

	snprintf(label, sizeof(label), "\"%s\"", fmt);
	PF_L(label, fmt);
}

DT_TEST(original_conversions, lone_percent, "\"%\": a format that is only '%'")
{
	format_alone("%");
}

DT_TEST(original_conversions, trailing_percent, "\"abc%\": '%' at the end of the format")
{
	format_alone("abc%");
}

DT_TEST(original_conversions, odd_percents, "\"%%%\": '%%' followed by a lone '%'")
{
	format_alone("%%%");
}

DT_TEST(original_conversions, unknown_conversion, "\"%k\": unknown conversion")
{
	format_alone("%k");
}

DT_TEST(original_conversions, unknown_inside_text, "\"a%Zb\": unknown conversion inside text")
{
	format_alone("a%Zb");
}

DT_TEST(original_conversions, null_format, "ft_printf(NULL): returns -1 and writes nothing")
{
	t_pfcap	cap;
	int		r;
	int		len;

	if (pf_capture_begin(&cap) != 0)
	{
		DT_FAILF("could not capture stdout");
		return ;
	}
	r = ft_printf(NULL);
	len = pf_capture_end(&cap, g_pf_got, PF_BUF_SIZE);
	DT_CHECK_INT("ft_printf(NULL) returns -1", r, -1);
	DT_CHECK_INT("ft_printf(NULL) writes nothing", len, 0);
}

DT_TEST(original_flags, width_alone, "\"%5\": width without a conversion")
{
	format_alone("%5");
}

DT_TEST(original_flags, minus_alone, "\"%-\": flag without a conversion")
{
	format_alone("%-");
}

DT_TEST(original_flags, dot_alone, "\"%.\": precision without a conversion")
{
	format_alone("%.");
}

DT_TEST(original_flags, width_unknown, "\"%5k\": width + unknown conversion")
{
	format_alone("%5k");
}

DT_TEST(original_flags, width_percent, "\"%5%\": width on '%%'")
{
	format_alone("%5%");
}

DT_TEST(original_flags, minus_width_percent, "\"%-5%|\": '-' and width on '%%'")
{
	format_alone("%-5%|");
}

DT_TEST(original_flags, zero_width_percent, "\"%05%\": '0' and width on '%%'")
{
	format_alone("%05%");
}

DT_TEST(original_flags, flag_mismatch, "flags that do not apply to the conversion (#, +, space, 0, precision)")
{
	/* '#' on non-hex */
	PF("%#d", 42);
	PF("%#s", "abc");
	PF("%#p", (void *)0x42);
	/* '+' and ' ' on unsigned / strings / chars / pointers */
	PF("%+u", 42u);
	PF("% x", 42u);
	PF("%+s", "abc");
	PF("% c", 'a');
	PF("%+p", (void *)0x42);
	/* '0' on strings / chars / pointers */
	PF("%05s", "abc");
	PF("%05c", 'a');
	PF("%020p", (void *)0x42);
	PF("%010p", NULL);
	/* precision on chars / pointers */
	PF("%.3c", 'a');
	PF("%.5p", (void *)0x42);
	PF("%.0p", NULL);
	/* combinations */
	PF("%-0+# 10.5d|", 42);
	PF("%-0+# 10.5x|", 42u);
}
