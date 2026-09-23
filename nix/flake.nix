{
  # Local mirror of .github/workflows/Aeon.VertiGate.yml.
  #
  # Each build job of the workflow is a script that runs the same steps, in the same order, against the working tree:
  #
  #   nix run ./nix#build-firmware          Build Firmware (hw0.1): MicroPython image with the application frozen in
  #   nix run ./nix#build-interface         Build Interface (Linux x64 debug and release): regenerate, build and pack the NuGet package
  #   nix run ./nix#configure-build         Print the CiBuildVersion, CiIsForRelease and CiFirmwarePreviewVersion exports
  #   nix run ./nix#lint                    actionlint (with shellcheck) over the workflow file
  #   nix run ./nix#ci                      lint, then both build jobs
  #   nix run ./nix#act -- push -j lint     Run the real workflow file under nektos/act
  #   nix develop ./nix                     Shell with the toolchain and all of the above on PATH
  #
  # The publish jobs are not mirrored: they need repository secrets and push to GitHub Packages and NuGet.org.
  # The Windows leg of the interface matrix is not mirrored either.
  # Outputs land under artifacts/, which is ignored by git, exactly where the workflow puts them.
  description = "Local mirror of the Aeon.VertiGate GitHub Actions workflow";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});

      # Toolchain. The workflow installs these with apt and setup-* actions; here they come from nixpkgs.
      firmwareTools = pkgs: with pkgs; [
        # Same GCC major as the gcc-arm-none-eabi and libnewlib-arm-none-eabi packages on ubuntu-latest. Newer releases turn mbedtls warnings into errors under MicroPython's -Werror.
        gcc-arm-embedded-13
        picotool # stands in for the picotool built by tools/ci.sh rp2_setup
        stdenv.cc # host compiler for mpy-cross and the pico-sdk host tools
        cmake
        gnumake
        python311
        uv
      ];
      interfaceTools = pkgs: with pkgs; [ dotnet-sdk_8 ];
      commonTools = pkgs: with pkgs; [ git gh coreutils gnused diffutils ];

      mkScripts = pkgs:
        let
          lib = builtins.readFile ./scripts/lib.sh;
          script = { name, runtimeInputs, preamble ? "" }:
            pkgs.writeShellApplication {
              inherit name runtimeInputs;
              text = lib + preamble + builtins.readFile ./scripts/${name}.sh;
            };
        in
        rec {
          configure-build = script {
            name = "configure-build";
            runtimeInputs = commonTools pkgs;
          };

          build-firmware = script {
            name = "build-firmware";
            runtimeInputs = commonTools pkgs ++ firmwareTools pkgs ++ [ configure-build ];
            preamble = ''
              # pico-sdk looks for an installed picotool before trying to fetch and build one.
              export picotool_DIR="${pkgs.picotool}/lib/cmake/picotool"
              # Prefer the Python on PATH over a uv-managed download.
              export UV_PYTHON_PREFERENCE=system
            '';
          };

          build-interface = script {
            name = "build-interface";
            runtimeInputs = commonTools pkgs ++ interfaceTools pkgs ++ [ configure-build ];
          };

          lint = script {
            name = "lint";
            runtimeInputs = commonTools pkgs ++ [ pkgs.actionlint pkgs.shellcheck ];
          };

          act = script {
            name = "act";
            runtimeInputs = commonTools pkgs ++ [ pkgs.act ];
          };

          ci = script {
            name = "ci";
            runtimeInputs = commonTools pkgs ++ [ lint build-firmware build-interface ];
          };
        };
    in
    {
      packages = forAllSystems (pkgs: mkScripts pkgs // { default = (mkScripts pkgs).ci; });

      apps = forAllSystems (pkgs:
        builtins.mapAttrs
          (name: drv: { type = "app"; program = "${drv}/bin/${name}"; })
          (mkScripts pkgs)
        // { default = { type = "app"; program = "${(mkScripts pkgs).ci}/bin/ci"; }; });

      devShells = forAllSystems (pkgs: {
        default = pkgs.mkShell {
          packages = commonTools pkgs ++ firmwareTools pkgs ++ interfaceTools pkgs
            ++ [ pkgs.act pkgs.actionlint pkgs.shellcheck ]
            ++ builtins.attrValues (mkScripts pkgs);
          env = {
            picotool_DIR = "${pkgs.picotool}/lib/cmake/picotool";
            UV_PYTHON_PREFERENCE = "system";
            DOTNET_NOLOGO = "true";
            DOTNET_CLI_TELEMETRY_OPTOUT = "true";
            DOTNET_GENERATE_ASPNET_CERTIFICATE = "false";
          };
        };
      });
    };
}
