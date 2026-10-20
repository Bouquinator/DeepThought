#include "sstyle.h"
#include <string.h>

static void	t_strncmp(const char *label,
	const char *s1, const char *s2, size_t n)
{
	int	ref;
	int	got;
	int	rsign;
	int	gsign;

	ref = strncmp(s1, s2, n);
	got = ft_strncmp((char *)s1, (char *)s2, n);
	rsign = (ref > 0) - (ref < 0);
	gsign = (got > 0) - (got < 0);
	if (!(rsign == gsign))
	{
		DT_FAILF("%s: expected sign %d, got sign %d", label, rsign, gsign);
	}
}

DT_TEST(ft_strncmp, equal, "equal")
{
	t_strncmp("equal", "hello", "hello", 5);
}

DT_TEST(ft_strncmp, s1_lt_s2, "s1 < s2")
{
	t_strncmp("s1 < s2", "abc", "abd", 3);
}

DT_TEST(ft_strncmp, s1_gt_s2, "s1 > s2")
{
	t_strncmp("s1 > s2", "abd", "abc", 3);
}

DT_TEST(ft_strncmp, n_0_to_0, "n=0 → 0")
{
	t_strncmp("n=0 → 0", "abc", "xyz", 0);
}

DT_TEST(ft_strncmp, equal_prefix_differ_after_n, "equal prefix, differ after n")
{
	t_strncmp("equal prefix, differ after n", "hello!", "hello?", 5);
}

DT_TEST(ft_strncmp, s1_shorter_nul_lt_h, "s1 shorter (NUL < 'h')")
{
	t_strncmp("s1 shorter (NUL < 'h')", "hi", "high", 4);
}

DT_TEST(ft_strncmp, s2_shorter_h_gt_nul, "s2 shorter ('h' > NUL)")
{
	t_strncmp("s2 shorter ('h' > NUL)", "high", "hi", 4);
}

DT_TEST(ft_strncmp, n_gt_strlen, "n > strlen: must stop at NUL, not read past it")
{
	t_strncmp("n > strlen equal strings", "hi", "hi", 100);
}

DT_TEST(ft_strncmp, unsigned_char_comparison, "unsigned char comparison: 0xFF (255 as unsigned) > 0x01 (1)")
{
	{
		char	u1[] = {(char)0xFF, '\0'};
		char	u2[] = {0x01, '\0'};
		t_strncmp("0xFF > 0x01 (unsigned)", u1, u2, 1);
	}
}
