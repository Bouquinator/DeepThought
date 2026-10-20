#include "sstyle.h"
#include <string.h>

DT_TEST(ft_bzero, zero_the_middle_4_edges_must, "zero the middle 4, edges must stay intact")
{
	char	ref[10];
	char	got[10];

	memset(ref, 0xFF, 10); memset(got, 0xFF, 10);
	memset(ref + 3, 0, 4); ft_bzero(got + 3, 4);
	DT_CHECK_MEM("zero middle 4 of 10, edges intact", got, ref, 10);

	memset(ref, 'B', 10); memset(got, 'B', 10);
	ft_bzero(got, 0);
	DT_CHECK_MEM("n=0 (no change)", got, ref, 10);
}

DT_TEST(ft_bzero, stress, "stress: 8192 bytes")
{
	{
		static char	rbig[8192];
		static char	gbig[8192];
		memset(rbig, 0xAA, 8192); memset(gbig, 0xAA, 8192);
		memset(rbig, 0, 8192);    ft_bzero(gbig, 8192);
		DT_CHECK_MEM("bzero 8192 bytes (stress)", gbig, rbig, 8192);
	}
}
