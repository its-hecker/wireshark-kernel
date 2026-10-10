/* SPDX-License-Identifier: GPL-2.0-only */
/* Read-only recovery preflight for ARM64, MODVERSIONS and legacy Clang CFI. */
#include <elf.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>

struct image { unsigned char *data; size_t size; Elf64_Ehdr header; };
struct symbol { char name[256]; uint32_t crc; };
static struct symbol *exports;
static size_t export_count;

static void fail(const char *format, ...)
{
    va_list args;
    va_start(args, format);
    vfprintf(stderr, format, args);
    va_end(args);
    fputc('\n', stderr);
    exit(1);
}

static int within(const struct image *image, uint64_t offset, uint64_t size)
{
    return offset <= image->size && size <= image->size - offset;
}

static Elf64_Shdr section(const struct image *image, size_t index)
{
    Elf64_Shdr value;
    if (index >= image->header.e_shnum)
        fail("Invalid ELF section index");
    memcpy(&value, image->data + image->header.e_shoff + index * sizeof(value), sizeof(value));
    if (value.sh_type != SHT_NOBITS && !within(image, value.sh_offset, value.sh_size))
        fail("ELF section exceeds file size");
    return value;
}

static const char *string_at(const struct image *image, Elf64_Shdr strings, size_t offset)
{
    const char *value;
    if (strings.sh_type != SHT_STRTAB || offset >= strings.sh_size)
        fail("Invalid ELF string offset");
    value = (const char *)image->data + strings.sh_offset + offset;
    if (!memchr(value, 0, strings.sh_size - offset))
        fail("Unterminated ELF string");
    return value;
}

static Elf64_Shdr named_section(const struct image *image, const char *name)
{
    Elf64_Shdr names = section(image, image->header.e_shstrndx);
    for (size_t index = 1; index < image->header.e_shnum; index++) {
        Elf64_Shdr value = section(image, index);
        if (!strcmp(string_at(image, names, value.sh_name), name)) {
            if (value.sh_type == SHT_NOBITS) fail("ELF section %s has no stored data", name);
            return value;
        }
    }
    fail("Missing ELF section %s", name);
    return names;
}

static struct image open_image(const char *path)
{
    struct image image = {0};
    FILE *file = fopen(path, "rb");
    long length;
    if (!file) fail("Cannot read %s: %s", path, strerror(errno));
    if (fseek(file, 0, SEEK_END) || (length = ftell(file)) < (long)sizeof(Elf64_Ehdr) ||
        length > 64 * 1024 * 1024 || fseek(file, 0, SEEK_SET))
        fail("Invalid module size: %s", path);
    image.size = (size_t)length;
    image.data = malloc(image.size);
    if (!image.data || fread(image.data, 1, image.size, file) != image.size)
        fail("Cannot read module bytes: %s", path);
    fclose(file);
    memcpy(&image.header, image.data, sizeof(image.header));
    if (memcmp(image.header.e_ident, ELFMAG, SELFMAG) ||
        image.header.e_ident[EI_CLASS] != ELFCLASS64 ||
        image.header.e_ident[EI_DATA] != ELFDATA2LSB ||
        image.header.e_ident[EI_VERSION] != EV_CURRENT ||
        image.header.e_version != EV_CURRENT || image.header.e_type != ET_REL ||
        image.header.e_machine != EM_AARCH64 || image.header.e_ehsize != sizeof(Elf64_Ehdr) ||
        image.header.e_shentsize != sizeof(Elf64_Shdr) || !image.header.e_shnum ||
        image.header.e_shstrndx >= image.header.e_shnum ||
        !within(&image, image.header.e_shoff, (uint64_t)image.header.e_shnum * sizeof(Elf64_Shdr)))
        fail("Not a valid little-endian ARM64 kernel module: %s", path);
    return image;
}

static const char *modinfo(const struct image *image, const char *key)
{
    Elf64_Shdr info = named_section(image, ".modinfo");
    size_t offset = 0, key_size = strlen(key);
    while (offset < info.sh_size) {
        const char *value = (const char *)image->data + info.sh_offset + offset;
        const char *end = memchr(value, 0, info.sh_size - offset);
        if (!end) fail("Unterminated module metadata");
        if ((size_t)(end - value) > key_size && !memcmp(value, key, key_size) && value[key_size] == '=')
            return value + key_size + 1;
        offset += (size_t)(end - value) + 1;
    }
    fail("Missing module metadata %s", key);
    return NULL;
}

static int compare_symbol(const void *left, const void *right)
{
    return strcmp(((const struct symbol *)left)->name, ((const struct symbol *)right)->name);
}

static void read_exports(const char *path)
{
    FILE *file = fopen(path, "r");
    char line[1024], crc_text[32], name[256], provider[512], kind[64], extra;
    size_t capacity = 0;
    if (!file) fail("Cannot read target kernel symbols: %s", path);
    while (fgets(line, sizeof(line), file)) {
        char *end;
        unsigned long crc;
        if (!strchr(line, '\n') && !feof(file)) fail("Oversized target symbol record");
        if (sscanf(line, "%31s %255s %511s %63s %c", crc_text, name, provider, kind, &extra) != 4)
            fail("Invalid target symbol record");
        errno = 0;
        crc = strtoul(crc_text, &end, 16);
        if (errno || end == crc_text || *end || crc > UINT32_MAX)
            fail("Invalid target symbol CRC");
        if (export_count == capacity) {
            capacity = capacity ? capacity * 2 : 1024;
            if (capacity > 131072) fail("Too many target exports");
            struct symbol *next = realloc(exports, capacity * sizeof(*exports));
            if (!next) fail("Cannot allocate target symbol table");
            exports = next;
        }
        strcpy(exports[export_count].name, name);
        exports[export_count++].crc = (uint32_t)crc;
    }
    if (ferror(file) || !export_count) fail("Empty or unreadable target symbol table");
    fclose(file);
    qsort(exports, export_count, sizeof(*exports), compare_symbol);
    for (size_t index = 1; index < export_count; index++)
        if (!strcmp(exports[index - 1].name, exports[index].name) && exports[index - 1].crc != exports[index].crc)
            fail("Conflicting target export %s", exports[index].name);
}

static uint32_t target_crc(const char *name)
{
    struct symbol key;
    if (strlen(name) >= sizeof(key.name)) fail("Oversized module symbol");
    strcpy(key.name, name);
    const struct symbol *match = bsearch(&key, exports, export_count, sizeof(*exports), compare_symbol);
    if (!match) fail("Target kernel does not export %s", name);
    return match->crc;
}

static void check_versions(const struct image *image)
{
    Elf64_Shdr versions = named_section(image, "__versions");
    int layout = 0;
    if (!versions.sh_size || versions.sh_size % 64) fail("Invalid module symbol-version table");
    for (size_t offset = 0; offset < versions.sh_size; offset += 64) {
        uint64_t crc;
        const unsigned char *record = image->data + versions.sh_offset + offset;
        const char *name = (const char *)record + 8;
        memcpy(&crc, record, sizeof(crc));
        if (!*name || !memchr(name, 0, 56) || crc > UINT32_MAX)
            fail("Invalid module symbol-version record");
        uint32_t expected = target_crc(name);
        if (crc != expected)
            fail("ABI mismatch for %s: module %08x, target %08x", name, (unsigned)crc, expected);
        if (!strcmp(name, "module_layout")) layout = 1;
    }
    if (!layout) fail("Module lacks module_layout version");
}

static int check_symbols(const struct image *image, int *cfi)
{
    Elf64_Shdr table = named_section(image, ".symtab");
    Elf64_Shdr strings = section(image, table.sh_link);
    int exported = 0;
    *cfi = 0;
    if (table.sh_type != SHT_SYMTAB || table.sh_entsize != sizeof(Elf64_Sym) || table.sh_size % sizeof(Elf64_Sym))
        fail("Invalid ELF symbol table");
    for (size_t offset = 0; offset < table.sh_size; offset += sizeof(Elf64_Sym)) {
        Elf64_Sym symbol;
        memcpy(&symbol, image->data + table.sh_offset + offset, sizeof(symbol));
        const char *name = string_at(image, strings, symbol.st_name);
        if (!strcmp(name, "__cfi_check") && symbol.st_shndx != SHN_UNDEF) {
            if (symbol.st_shndx >= image->header.e_shnum || ELF64_ST_TYPE(symbol.st_info) != STT_FUNC || !symbol.st_size)
                fail("Invalid legacy CFI entry point");
            Elf64_Shdr code = section(image, symbol.st_shndx);
            if (code.sh_type != SHT_PROGBITS || symbol.st_value > code.sh_size || symbol.st_size > code.sh_size - symbol.st_value)
                fail("CFI entry point exceeds its section");
            *cfi = 1;
        }
        if (!strncmp(name, "__kcfi_typeid_", 14)) fail("KCFI module cannot be used with this legacy-CFI kernel");
        if (!strncmp(name, "__crc_", 6) && symbol.st_shndx == SHN_ABS) {
            if (symbol.st_value > UINT32_MAX || target_crc(name + 6) != symbol.st_value)
                fail("Exported-symbol ABI mismatch for %s", name + 6);
            exported++;
        }
    }
    return exported;
}

static void check_export_set(const struct image *installed, const struct image *reference)
{
    Elf64_Shdr expected = named_section(reference, ".symtab");
    Elf64_Shdr actual = named_section(installed, ".symtab");
    Elf64_Shdr expected_names = section(reference, expected.sh_link);
    Elf64_Shdr actual_names = section(installed, actual.sh_link);
    for (size_t offset = 0; offset < expected.sh_size; offset += sizeof(Elf64_Sym)) {
        Elf64_Sym symbol;
        memcpy(&symbol, reference->data + expected.sh_offset + offset, sizeof(symbol));
        const char *name = string_at(reference, expected_names, symbol.st_name);
        if (strncmp(name, "__crc_", 6) || symbol.st_shndx != SHN_ABS) continue;
        int found = 0;
        for (size_t next = 0; next < actual.sh_size; next += sizeof(Elf64_Sym)) {
            Elf64_Sym candidate;
            memcpy(&candidate, installed->data + actual.sh_offset + next, sizeof(candidate));
            if (candidate.st_shndx == SHN_ABS && candidate.st_value == symbol.st_value &&
                !strcmp(name, string_at(installed, actual_names, candidate.st_name))) {
                found = 1;
                break;
            }
        }
        if (!found) fail("Module is missing expected export %s", name + 6);
    }
}

int main(int argc, char **argv)
{
    if (argc != 4) fail("Usage: module-check installed.ko reference.ko target-Module.symvers");
    struct image installed = open_image(argv[1]), reference = open_image(argv[2]);
    if (strcmp(modinfo(&installed, "name"), modinfo(&reference, "name")))
        fail("Module name differs from this build");
    if (strcmp(modinfo(&installed, "vermagic"), modinfo(&reference, "vermagic")))
        fail("Module vermagic differs from this build");
    if (named_section(&installed, ".gnu.linkonce.this_module").sh_size !=
        named_section(&reference, ".gnu.linkonce.this_module").sh_size)
        fail("Module structure size differs from this build");
    read_exports(argv[3]);
    check_versions(&reference);
    check_versions(&installed);
    int actual_cfi, expected_cfi;
    int expected_exports = check_symbols(&reference, &expected_cfi);
    int actual_exports = check_symbols(&installed, &actual_cfi);
    if (actual_cfi != expected_cfi) fail("Module CFI mode differs from this build");
    if (actual_exports != expected_exports) fail("Module exported-symbol count differs from this build");
    check_export_set(&installed, &reference);
    free(installed.data);
    free(reference.data);
    free(exports);
    return 0;
}
