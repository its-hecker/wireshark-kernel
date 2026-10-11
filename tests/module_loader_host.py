"""Compile and exercise the actual module-loader CRC and vermagic functions."""
from pathlib import Path
import subprocess
import tempfile


def function(source, name):
    start = source.index(name)
    opening = source.index('{', start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[opening:end]


def main():
    source = (Path(__file__).resolve().parent.parent / 'kernel/module.c').read_text()
    preamble = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
typedef uint32_t u32;
typedef int32_t s32;
typedef struct { uintptr_t sh_addr; size_t sh_size; } Elf_Shdr;
struct module { int unused; };
struct modversion_info { unsigned long crc; char name[56]; };
struct load_info { Elf_Shdr *sechdrs; struct { unsigned int vers; } index; const char *name; };
#define CONFIG_MODULE_REL_CRCS 0
#define IS_ENABLED(value) (value)
#define pr_debug(...) ((void)0)
#define pr_warn(...) ((void)0)
#define pr_warn_once(...) ((void)0)
static int try_to_force_load(struct module *mod, const char *name)
{ (void)mod; (void)name; return -1; }
static u32 resolve_rel_crc(const s32 *crc) { return (u32)*crc; }
static int check_version(const struct load_info *info, const char *symname,
                         struct module *mod, const s32 *crc)
'''
    program = preamble + function(source, 'static int check_version(')
    program += '\nstatic int same_magic(const char *amagic, const char *bmagic, bool has_crcs)\n'
    program += function(source, 'static inline int same_magic(')
    program += r'''
int main(void) {
    struct modversion_info version = { 0x1234, "module_layout" };
    Elf_Shdr sections[2] = {{0, 0}, {(uintptr_t)&version, sizeof(version)}};
    struct load_info info = { sections, {1}, "example" };
    struct module mod = {0};
    s32 crc = 0x1234;
    assert(check_version(&info, "module_layout", &mod, &crc) == 1);
    crc = 0x5678;
    assert(check_version(&info, "module_layout", &mod, &crc) == 0);
    assert(check_version(&info, "module_layout", &mod, NULL) == 1);
    info.index.vers = 0;
    assert(check_version(&info, "module_layout", &mod, &crc) == 0);
    const char *wire = "4.14.357-WireShark+ SMP preempt mod_unload modversions aarch64";
    const char *lineage = "4.14.357-openela SMP preempt mod_unload modversions aarch64";
    assert(same_magic(wire, lineage, true));
    assert(!same_magic(wire, lineage, false));
    assert(same_magic(wire, wire, false));
    assert(!same_magic(wire, "4.14.357-openela SMP mod_unload modversions aarch64", true));
    return 0;
}
'''
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / 'loader.c').write_text(program)
        subprocess.run(['cc', '-std=c99', '-O2', '-Wall', '-Wextra', '-Werror',
                        str(root / 'loader.c'), '-o', str(root / 'loader')], check=True)
        subprocess.run([str(root / 'loader')], check=True)
    print('8 actual module-loader CRC/vermagic regression cases passed')


if __name__ == '__main__':
    main()
