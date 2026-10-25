#!/usr/bin/env node
/** Verify discovery with the installed DSH parser, without calling a model. */
import assert from 'node:assert/strict';
import { readFile, stat } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { homedir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const usage = `Usage: node scripts/verify-dsh.mjs --dsh-package-root <path/to/@deepseek-ai/dsh>
  [--dsh-home <path/to/.dsh>] [--cwd <workspace>]

DSH_PACKAGE_ROOT and DSH_HOME can supply the corresponding paths.
This loads DSH's real filesystem skill provider without starting DSH or a model.`;

function argumentsFor(argv) {
  const options = {};
  for (let index = 0; index < argv.length; index += 1) {
    const flag = argv[index];
    if (flag === '--help' || flag === '-h') return { help: true };
    if (!['--dsh-package-root', '--dsh-home', '--cwd'].includes(flag)) {
      throw new Error(`Unknown option: ${flag}`);
    }
    const value = argv[++index];
    if (!value || value.startsWith('--')) throw new Error(`Missing value for ${flag}`);
    options[flag.slice(2)] = value;
  }
  return options;
}

async function main() {
  const options = argumentsFor(process.argv.slice(2));
  if (options.help) {
    console.log(usage);
    return;
  }
  const rootArgument = options['dsh-package-root'] || process.env.DSH_PACKAGE_ROOT;
  if (!rootArgument) throw new Error(`Provide --dsh-package-root or DSH_PACKAGE_ROOT.\n${usage}`);
  const packageRoot = resolve(rootArgument);
  const manifest = JSON.parse(await readFile(join(packageRoot, 'package.json'), 'utf8'));
  assert.equal(manifest.name, '@deepseek-ai/dsh', 'The package root must point to @deepseek-ai/dsh');
  const requireFromDsh = createRequire(pathToFileURL(join(packageRoot, 'package.json')));
  const providerUrl = pathToFileURL(requireFromDsh.resolve('@deepseek-ai/dsh-skill-filesystem'));
  const { FileSystemSkillProvider } = await import(providerUrl.href);
  const home = resolve(options['dsh-home'] || process.env.DSH_HOME || join(homedir(), '.dsh'));
  const workspace = resolve(options.cwd || process.cwd());
  const controller = new AbortController();
  const warnings = [];
  const context = { get: () => undefined, logger: { warn: message => warnings.push(String(message)) } };
  const provider = new FileSystemSkillProvider(context, {
    signal: controller.signal, invalidate() {},
  }, { dshHome: home, watch: false });

  try {
    const result = await provider.list({ cwd: workspace, signal: controller.signal });
    assert.ok(Array.isArray(result) || result.complete !== false, 'DSH discovery was incomplete');
    const candidates = Array.isArray(result) ? result : result.candidates;
    const expectedPath = resolve(home, 'skills', 'dsh-property-lab', 'SKILL.md');
    const candidate = candidates.find(item => item.name === 'dsh-property-lab'
      && item.source === 'user-dsh' && resolve(item.locator.path) === expectedPath);
    assert.ok(candidate, `DSH did not discover the installed skill at ${expectedPath}`);
    const loaded = await provider.get(candidate, { signal: controller.signal });
    assert.ok(loaded, 'DSH could not load the discovered skill');
    assert.equal(loaded.invocation.modelInvocable, true);
    assert.equal(loaded.invocation.userInvocable, true);
    assert.ok(loaded.content.trim().length > 0, 'The skill body is empty');
    for (const relative of ['scripts/run.py', 'runtime.json', 'references/spec-format.md']) {
      assert.ok((await stat(join(home, 'skills', 'dsh-property-lab', relative))).isFile(),
        `Installed resource is missing: ${relative}`);
    }
    console.log(JSON.stringify({
      verified: true, dsh_version: manifest.version, name: loaded.name,
      source: loaded.source, invocation: loaded.invocation,
      skill_path: expectedPath, body_bytes: Buffer.byteLength(loaded.content),
      discovery_warning_count: warnings.length, model_api_used: false,
    }, null, 2));
  } finally {
    await provider.dispose();
    controller.abort();
  }
}

try { await main(); }
catch (error) {
  console.error(`DSH verification failed: ${error.message}`);
  process.exitCode = 1;
}
