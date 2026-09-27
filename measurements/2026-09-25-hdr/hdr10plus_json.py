#!/usr/bin/env python3
"""Metadane HDR10+ (ST 2094-40) w formacie JSON dla x265 --dhdr10-info.

Dwie sceny po polowie klatek: jasna (MaxSCL ~1000 nitow) i ciemna (~150 nitow),
zeby dynamiczne mapowanie tonow roznilo sie miedzy scenami.
Uzycie: hdr10plus_json.py <klatek> <plik.json>
"""
import json
import sys


def scena(idx_sceny, klatka_w_scenie, klatka, jasna):
    maks = [10000, 9000, 8000] if jasna else [1500, 1400, 1300]      # 0,1 cd/m^2 * 10
    srednia = 2000 if jasna else 300
    rozklad = [5, 10, 25, 50, 75, 90, 95, 99] if jasna else [1, 2, 5, 10, 20, 40, 60, 90]
    return {
        'BezierCurveData': {'Anchors': [102, 205, 307, 410, 512, 614, 717, 819, 922],
                            'KneePointX': 0, 'KneePointY': 0},
        'LuminanceParameters': {
            'AverageRGB': srednia,
            'LuminanceDistributions': {
                'DistributionIndex': [1, 5, 10, 25, 50, 75, 90, 95, 99],
                'DistributionValues': [0] + [v * (100 if jasna else 15) for v in rozklad],
            },
            'MaxScl': maks,
        },
        'NumberOfWindows': 1,
        'TargetedSystemDisplayMaximumLuminance': 400,
        'SceneFrameIndex': klatka_w_scenie,
        'SceneId': idx_sceny,
        'SequenceFrameIndex': klatka,
    }


def main():
    n = int(sys.argv[1])
    pol = n // 2
    klatki = [scena(0 if i < pol else 1, i if i < pol else i - pol, i, i < pol) for i in range(n)]
    dane = {
        'JSONInfo': {'HDR10plusProfile': 'B', 'Version': '1.0'},
        'SceneInfo': klatki,
        'SceneInfoSummary': {'SceneFirstFrameIndex': [0, pol], 'SceneFrameNumbers': [pol, n - pol]},
        'ToolInfo': {'Tool': 's10plus-hdr10plus_json.py', 'Version': '1.0'},
    }
    json.dump(dane, open(sys.argv[2], 'w'), indent=1)
    print('scen 2, klatek', n)


if __name__ == '__main__':
    main()
