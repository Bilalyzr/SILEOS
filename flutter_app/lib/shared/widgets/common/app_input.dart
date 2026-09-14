// lib/shared/widgets/common/app_input.dart
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

enum InputType { text, email, password, number, phone, multiline }

class AppInput extends StatefulWidget {
  final String? label;
  final String? hint;
  final String? helperText;
  final String? errorText;
  final TextEditingController? controller;
  final ValueChanged<String>? onChanged;
  final VoidCallback? onTap;
  final bool readOnly;
  final bool enabled;
  final int? maxLines;
  final int? maxLength;
  final TextInputType? keyboardType;
  final List<TextInputFormatter>? inputFormatters;
  final Widget? prefixIcon;
  final Widget? suffixIcon;
  final bool obscureText;
  final InputBorder? border;
  final EdgeInsets? contentPadding;
  final String? Function(String?)? validator;
  final AutovalidateMode? autovalidateMode;
  final TextInputAction? textInputAction;
  final ValueChanged<String>? onFieldSubmitted;
  final FocusNode? focusNode;
  final TextCapitalization textCapitalization;

  const AppInput({
    super.key,
    this.label,
    this.hint,
    this.helperText,
    this.errorText,
    this.controller,
    this.onChanged,
    this.onTap,
    this.readOnly = false,
    this.enabled = true,
    this.maxLines = 1,
    this.maxLength,
    this.keyboardType,
    this.inputFormatters,
    this.prefixIcon,
    this.suffixIcon,
    this.obscureText = false,
    this.border,
    this.contentPadding,
    this.validator,
    this.autovalidateMode,
    this.textInputAction,
    this.onFieldSubmitted,
    this.focusNode,
    this.textCapitalization = TextCapitalization.none,
  });

  @override
  State<AppInput> createState() => _AppInputState();
}

class _AppInputState extends State<AppInput> {
  late bool _obscureText;

  @override
  void initState() {
    super.initState();
    _obscureText = widget.obscureText;
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final effectiveBorder = widget.border ??
        OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: BorderSide(color: theme.dividerColor),
        );

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        if (widget.label != null) ...[
          Text(
            widget.label!,
            style: theme.textTheme.bodyMedium?.copyWith(
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 8),
        ],
        TextFormField(
          controller: widget.controller,
          focusNode: widget.focusNode,
          onChanged: widget.onChanged,
          onTap: widget.onTap,
          readOnly: widget.readOnly,
          enabled: widget.enabled,
          maxLines: widget.obscureText ? 1 : widget.maxLines,
          maxLength: widget.maxLength,
          keyboardType: widget.keyboardType,
          inputFormatters: widget.inputFormatters,
          obscureText: _obscureText,
          validator: widget.validator,
          autovalidateMode: widget.autovalidateMode,
          textInputAction: widget.textInputAction,
          textCapitalization: widget.textCapitalization,
          onFieldSubmitted: widget.onFieldSubmitted,
          decoration: InputDecoration(
            hintText: widget.hint,
            helperText: widget.helperText,
            helperMaxLines: 2,
            errorText: widget.errorText,
            prefixIcon: widget.prefixIcon,
            suffixIcon: _buildSuffixIcon(),
            border: effectiveBorder,
            enabledBorder: effectiveBorder,
            focusedBorder: effectiveBorder.copyWith(
              borderSide: BorderSide(color: theme.colorScheme.primary),
            ),
            errorBorder: effectiveBorder.copyWith(
              borderSide: BorderSide(color: theme.colorScheme.error),
            ),
            focusedErrorBorder: effectiveBorder.copyWith(
              borderSide: BorderSide(color: theme.colorScheme.error),
            ),
            filled: !widget.enabled,
            fillColor: widget.enabled ? null : theme.disabledColor.withOpacity(0.1),
            contentPadding: widget.contentPadding ??
                const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            counterText: '',
          ),
        ),
      ],
    );
  }

  Widget? _buildSuffixIcon() {
    if (widget.obscureText) {
      return IconButton(
        icon: Icon(_obscureText ? Icons.visibility_off : Icons.visibility),
        onPressed: () {
          setState(() => _obscureText = !_obscureText);
        },
      );
    }
    return widget.suffixIcon;
  }
}
