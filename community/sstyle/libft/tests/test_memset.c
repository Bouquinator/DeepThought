#include "sstyle.h"
#include <string.h>

DT_TEST(ft_memset, basic, "ft_memset: basic cases")
{
	char	ref[32];
	char	got[32];

	memset(ref, 'A', 10); ft_memset(got, 'A', 10);
	DT_CHECK_MEM("fill 10 with 'A'", got, ref, 10);

	memset(ref, 'X', 4); memset(got, 'X', 4);
	memset(ref, 0, 0); ft_memset(got, 0, 0);
	DT_CHECK_MEM("n=0 (no change)", got, ref, 4);

	char	buf[4] = {0};
	void	*ret = ft_memset(buf, 1, 4);
	DT_CHECK_PTR("returns dst pointer", ret, (void *)buf);
}

DT_TEST(ft_memset, value_gt_127, "value > 127: int c is truncated to unsigned char")
{
	{
		char	rbuf2[4];
		char	gbuf2[4];
		memset(rbuf2, 200, 4);
		ft_memset(gbuf2, 200, 4);
		DT_CHECK_MEM("fill 4 with 200 (high byte cast)", gbuf2, rbuf2, 4);
	}
}

DT_TEST(ft_memset, guard_bytes, "guard bytes: only first n bytes change, tail is intact")
{
	{
		char	rbuf3[8];
		char	gbuf3[8];
		memset(rbuf3, 0xFF, 8); memset(gbuf3, 0xFF, 8);
		memset(rbuf3, 0, 4);    ft_memset(gbuf3, 0, 4);
		DT_CHECK_MEM("guard bytes: only first 4 zeroed", gbuf3, rbuf3, 8);
	}
}

DT_TEST(ft_memset, stress, "stress: large buffer (4096 bytes)")
{
	{
		static char	rbig[4096];
		static char	gbig[4096];
		memset(rbig, 'Z', 4096);
		ft_memset(gbig, 'Z', 4096);
		DT_CHECK_MEM("fill 4096 with 'Z' (stress)", gbig, rbig, 4096);
	}
}
