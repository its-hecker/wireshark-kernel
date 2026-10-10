"""Observable recovery-preflight cases, using small ELF64 ARM64 fixtures."""
from pathlib import Path
import hashlib
import struct
import subprocess
import sys
import tempfile


def module(path, *, version='4.14.357-WireShark+ SMP preempt mod_unload modversions aarch64',
           name='example', imports=None, exports=None, cfi=True, machine=183):
    if imports is None:
        imports = {'module_layout': 0x1234, 'api_fn': 0x5678}
    if exports is None:
        exports = {'owned_fn': 0x9abc}
    names = ['.text', '.modinfo', '.gnu.linkonce.this_module', '__versions', '.strtab', '.symtab', '.shstrtab']
    section_names = b'\0'
    section_offsets = {}
    for item in names:
        section_offsets[item] = len(section_names)
        section_names += item.encode() + b'\0'
    strings = b'\0'
    symbols = bytes(24)
    if cfi:
        pos = len(strings)
        strings += b'__cfi_check\0'
        symbols += struct.pack('<IBBHQQ', pos, 0x12, 0, 1, 0, 4)
    for key, crc in exports.items():
        pos = len(strings)
        strings += b'__crc_' + key.encode() + b'\0'
        symbols += struct.pack('<IBBHQQ', pos, 0x10, 0, 0xfff1, crc, 0)
    metadata = f'name={name}\0vermagic={version}\0'.encode()
    versions = b''.join(struct.pack('<Q', value) + key.encode().ljust(56, b'\0') for key, value in imports.items())
    payloads = [struct.pack('<I', 0xd65f03c0), metadata, bytes(896), versions, strings, symbols, section_names]
    data = bytearray(64)
    sections = [bytes(64)]
    for index, (key, payload) in enumerate(zip(names, payloads), 1):
        while len(data) % 8:
            data.append(0)
        offset = len(data)
        data.extend(payload)
        kind = 3 if key in ('.strtab', '.shstrtab') else 2 if key == '.symtab' else 1
        sections.append(struct.pack('<IIQQQQIIQQ', section_offsets[key], kind, 0, 0,
                                    offset, len(payload), 5 if key == '.symtab' else 0, 0, 8,
                                    24 if key == '.symtab' else 0))
    while len(data) % 8:
        data.append(0)
    offset = len(data)
    data.extend(b''.join(sections))
    ident = b'\x7fELF\x02\x01\x01' + bytes(9)
    data[:64] = struct.pack('<16sHHIQQQIHHHHHH', ident, 1, machine, 1, 0, 0, offset, 0, 64, 0, 0, 64, 8, 7)
    path.write_bytes(data)


def main():
    checker = str(Path(sys.argv[1]).resolve())
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        reference, installed, symbols = (root / name for name in ('reference.ko', 'installed.ko', 'Module.symvers'))
        symbols.write_text('0x00001234 module_layout vmlinux EXPORT_SYMBOL\n'
                           '0x00005678 api_fn vmlinux EXPORT_SYMBOL\n'
                           '0x00009abc owned_fn example EXPORT_SYMBOL\n'
                           '0x0000abcd other_fn other EXPORT_SYMBOL\n'
                           '0x8f678b07 __stack_chk_guard vmlinux EXPORT_SYMBOL\n')
        module(reference)
        cases = [
            ('same ABI', {}, True, ''),
            ('compiler adds supported stack guard', {'imports': {'module_layout': 0x1234, 'api_fn': 0x5678, '__stack_chk_guard': 0x8f678b07}}, True, ''),
            ('different release', {'version': '4.14.261 incompatible'}, False, 'vermagic'),
            ('different module', {'name': 'other'}, False, 'name'),
            ('changed imported ABI', {'imports': {'module_layout': 0x1234, 'api_fn': 0x5679}}, False, 'ABI mismatch for api_fn'),
            ('unknown kernel import', {'imports': {'module_layout': 0x1234, 'unknown': 0x5678}}, False, 'does not export unknown'),
            ('changed module layout', {'imports': {'module_layout': 0x1235, 'api_fn': 0x5678}}, False, 'module_layout'),
            ('missing module layout', {'imports': {'api_fn': 0x5678}}, False, 'module_layout'),
            ('empty symbol versions', {'imports': {}}, False, 'symbol-version table'),
            ('changed module export', {'exports': {'owned_fn': 0x9abd}}, False, 'Exported-symbol ABI mismatch'),
            ('substituted export', {'exports': {'other_fn': 0xabcd}}, False, 'missing expected export'),
            ('removed export', {'exports': {}}, False, 'exported-symbol count'),
            ('different CFI mode', {'cfi': False}, False, 'CFI mode'),
            ('wrong architecture', {'machine': 62}, False, 'ARM64'),
        ]
        for label, settings, success, message in cases:
            module(installed, **settings)
            result = subprocess.run([checker, str(installed), str(reference), str(symbols)], capture_output=True, text=True)
            assert (result.returncode == 0) == success, (label, result.stderr)
            assert success or message in result.stderr, (label, result.stderr)
        installed.write_bytes(b'broken')
        result = subprocess.run([checker, str(installed), str(reference), str(symbols)], capture_output=True, text=True)
        assert result.returncode != 0 and 'module size' in result.stderr

        # Run the actual shell preflight with temporary module roots and a core stub.
        # Stop at the partition checks; the marker represents the first possible write.
        project = Path(__file__).resolve().parent.parent
        installer = (project / 'anykernel.sh').read_text().split('case "$SLOT"')[0]
        tools = root / 'tools'
        tools.mkdir()
        (tools / 'ak3-core.sh').write_text('abort() { echo "$*" >&2; exit 1; }\nui_print() { echo "$*"; }\n')
        (tools / 'module-check').symlink_to(checker)
        refs, vendor = root / 'module-reference', root / 'vendor'
        refs.mkdir()
        vendor.mkdir()
        module(refs / 'example.ko')
        for payload in ('Image.lz4', 'dtb', 'dtbo.img'):
            (root / payload).write_bytes(b'fixture')
        (root / 'module-symbols.txt').write_bytes(symbols.read_bytes())
        digest = hashlib.sha256((refs / 'example.ko').read_bytes()).hexdigest()
        (root / 'modules.sha256').write_text(f'{digest} example.ko\n')
        old_roots = '/vendor/lib/modules /system/vendor/lib/modules /vendor_dlkm/lib/modules /system/lib/modules'
        installer = installer.replace(old_roots, str(vendor)) + 'echo partition-write > write-marker\n'
        (root / 'preflight.sh').write_text(installer)
        for label, settings, success, message in [
            ('hash differs but ABI matches', {'imports': {'module_layout': 0x1234, 'api_fn': 0x5678, '__stack_chk_guard': 0x8f678b07}}, True, 'ABI checks passed'),
            ('bad ABI stops before writes', {'imports': {'module_layout': 0x1235}}, False, 'No partitions were changed'),
            ('missing Vendor module', None, False, 'unavailable. Mount Vendor'),
        ]:
            candidate = vendor / 'example.ko'
            if settings is None:
                candidate.unlink()
            else:
                module(candidate, **settings)
            marker = root / 'write-marker'
            marker.unlink(missing_ok=True)
            result = subprocess.run(['sh', 'preflight.sh'], cwd=root, capture_output=True, text=True)
            assert (result.returncode == 0) == success, (label, result.stdout, result.stderr)
            assert marker.exists() == success, label
            assert message in result.stdout + result.stderr, (label, result.stdout, result.stderr)
    print('18 module ABI and installer-preflight regression cases passed')


if __name__ == '__main__':
    main()
