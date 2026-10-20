#include "sstyle.h"
#include <string.h>

static void	t_memcmp(const char *label,
	const void *s1, const void *s2, size_t n)
{
	int	ref;
	int	got;
	int	rsign;
	int	gsign;

	ref = memcmp(s1, s2, n);
	got = ft_memcmp(s1, s2, n);
	rsign = (ref > 0) - (ref < 0);
	gsign = (got > 0) - (got < 0);
	if (!(rsign == gsign))
	{
		DT_FAILF("%s: expected sign %d, got sign %d (ref=%d, got=%d)", label, rsign, gsign, ref, got);
	}
}

DT_TEST(ft_memcmp, equal, "equal")
{
	t_memcmp("equal", "hello", "hello", 5);
}

DT_TEST(ft_memcmp, s1_lt_s2, "s1 < s2")
{
	t_memcmp("s1 < s2", "abc", "abd", 3);
}

DT_TEST(ft_memcmp, s1_gt_s2, "s1 > s2")
{
	t_memcmp("s1 > s2", "abd", "abc", 3);
}

DT_TEST(ft_memcmp, n_0_to_0, "n=0 → 0")
{
	t_memcmp("n=0 → 0", "abc", "xyz", 0);
}

DT_TEST(ft_memcmp, equal_first_n_bytes_differ_after, "equal first n bytes, differ after")
{
	t_memcmp("equal n bytes, differ after n", "abcXXX", "abcYYY", 3);
}

DT_TEST(ft_memcmp, must_not_stop_at_0x00_and, "must not stop at 0x00, and must compare as unsigned (0xFF > 0x00)")
{
	unsigned char	b1[] = {0x00, 0x01, 0xFF};
	unsigned char	b2[] = {0x00, 0x01, 0x00};

	t_memcmp("binary: past 0x00, 0xFF > 0x00", b1, b2, 3);
}
