#include "sstyle.h"
#include <string.h>

DT_TEST(ft_memmove, basic, "ft_memmove: basic cases")
{
	char	ref[24];
	char	got[24];

	memset(ref, 0, 24); memset(got, 0, 24);
	strcpy(ref, "Hello"); strcpy(got, "Hello");
	memmove(ref + 10, ref, 6); ft_memmove(got + 10, got, 6);
	DT_CHECK_MEM("non-overlapping copy", got + 10, ref + 10, 6);

	strcpy(ref, "Hello"); strcpy(got, "Hello");
	memmove(ref + 2, ref, 4); ft_memmove(got + 2, got, 4);
	DT_CHECK_MEM("overlap: dst > src (shift right)", got, ref, 8);

	strcpy(ref, "  Hello"); strcpy(got, "  Hello");
	memmove(ref, ref + 2, 6); ft_memmove(got, got + 2, 6);
	DT_CHECK_MEM("overlap: dst < src (shift left)", got, ref, 7);

	strcpy(ref, "Test"); strcpy(got, "Test");
	memmove(ref + 2, ref, 0); ft_memmove(got + 2, got, 0);
	DT_CHECK_MEM("n=0 (no change)", got, ref, 4);

	char	buf[10] = "ABCDE";
	void	*ret = ft_memmove(buf + 2, buf, 3);
	DT_CHECK_PTR("returns dest pointer", ret, (void *)(buf + 2));
}

DT_TEST(ft_memmove, src_eq_dst, "src == dst: must be a no-op")
{
	{
		char	same[8] = "ABCDEFG";
		char	ref2[8];
		memcpy(ref2, same, 8);
		ft_memmove(same, same, 4);
		DT_CHECK_MEM("memmove src==dst (no change)", same, ref2, 8);
	}
}

DT_TEST(ft_memmove, large_overlapping_copy_512_bytes_shift, "large overlapping copy (512 bytes, shift by 1)")
{
	{
		static char	rbig[513];
		static char	gbig[513];
		memset(rbig, 'Q', 512); rbig[512] = '\0';
		memset(gbig, 'Q', 512); gbig[512] = '\0';
		memmove(rbig + 1, rbig, 511);
		ft_memmove(gbig + 1, gbig, 511);
		DT_CHECK_MEM("memmove 511-byte rightward shift (stress)", gbig, rbig, 512);
	}
}
