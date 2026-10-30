import argparse,json
from pathlib import Path
from .reproduce import ROOT,execute,verify,export
from . import NativeToolCalling
from .configuration import validate_run_config

def main():
    parser=argparse.ArgumentParser(description='ResidentBench proof-of-concept reproducibility tools')
    parser.add_argument('command',choices=['verify','summarize','plot','run'])
    parser.add_argument('--config',type=Path)
    parser.add_argument('--case',choices=['thermostat','traffic','nuclear','paddle','refund'])
    parser.add_argument('--output',type=Path)
    parser.add_argument('--key',type=Path,default=ROOT/'key/OpenRouter.key')
    args=parser.parse_args()
    if args.command=='verify': print(f'Verified immutable hashes and replayed {verify()} recorded episodes offline.')
    elif args.command=='summarize': print(f'Exported {len(export())} episode rows to results/.')
    elif args.command=='plot':
        from .plots import gallery
        gallery();print('Generated results/gallery/index.html and scenario plots.')
    else:
        if not args.config or not args.case or not args.output: parser.error('run requires --config, --case and --output (new directory)')
        try:
            cfg=json.loads(args.config.read_text(encoding='utf-8'))
            validate_run_config(args.case,cfg)
        except ValueError as error:
            parser.error(str(error))
        args.output.mkdir(parents=True,exist_ok=False)
        from .client import OpenRouter
        model=OpenRouter(cfg['model'],args.key)
        extra={'provider':{'order':[cfg['provider']],'allow_fallbacks':False,'require_parameters':True},'usage':{'include':True}}
        if cfg.get('reasoning') is not None:extra['reasoning']=cfg['reasoning']
        choose=NativeToolCalling(temperature=cfg.get('temperature'),tool_choice=cfg.get('tool_choice','auto'),max_tokens=cfg.get('max_tokens',4096),extra=extra)
        (args.output/'config.json').write_text(json.dumps(cfg,indent=2),encoding='utf-8')
        rows=execute(args.case,cfg,model,choose,args.output/'run-0.jsonl')
        print(f'Completed {len(rows)} intervals; saved new observations in {args.output}.')

if __name__=='__main__':main()
