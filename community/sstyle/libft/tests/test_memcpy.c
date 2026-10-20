#include "sstyle.h"
#include <string.h>

DT_TEST(ft_memcpy, partial_copy, "partial copy: bytes after n must stay intact")
{
	const char	src[] = "Hello, World!";
	char		ref[20];
	char		got[20];

	memset(ref, 'X', 20); memset(got, 'X', 20);
	memcpy(ref, src, 5); ft_memcpy(got, src, 5);
	DT_CHECK_MEM("copy 5 bytes, tail intact", got, ref, 20);

	memset(ref, 'X', 4); memset(got, 'X', 4);
	memcpy(ref, src, 0); ft_memcpy(got, src, 0);
	DT_CHECK_MEM("n=0 (no change)", got, ref, 4);

	char	dst[10] = {0};
	void	*ret = ft_memcpy(dst, src, 5);
	DT_CHECK_PTR("returns dst pointer", ret, (void *)dst);
}

DT_TEST(ft_memcpy, binary_data_with_embedded_zeros, "binary data with embedded zeros")
{
	{
		const unsigned char	bsrc[] = {0x00, 0x01, 0xFF, 0x7F, 0x80, 0x42};
		unsigned char		rbuf[6];
		unsigned char		gbuf[6];
		memcpy(rbuf, bsrc, 6);
		ft_memcpy(gbuf, bsrc, 6);
		DT_CHECK_MEM("copy binary with embedded zero", gbuf, rbuf, 6);
	}
}

DT_TEST(ft_memcpy, stress, "stress: 1024-byte copy")
{
	{
		static char	src3[1024];
		static char	rbig[1024];
		static char	gbig[1024];
		memset(src3, 'P', 1024);
		memcpy(rbig, src3, 1024);
		ft_memcpy(gbig, src3, 1024);
		DT_CHECK_MEM("copy 1024 bytes (stress)", gbig, rbig, 1024);
	}
}
