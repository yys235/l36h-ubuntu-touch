/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Sony Yuga only. Values from board-sony_fusion3_yuga.c. No ALS/RGB setup. */
static bool lm3533_is_yuga(struct device *dev)
{
	return of_machine_is_compatible("sony,xperia-yuga") &&
		of_device_is_compatible(dev->of_node, "sony,yuga-lm3533");
}

static int lm3533_yuga_platform_data(struct device *dev)
{
	struct lm3533_platform_data *data;
	struct lm3533_bl_platform_data *bl;

	if (!lm3533_is_yuga(dev))
		return 0;
	data = devm_kzalloc(dev, sizeof(*data), GFP_KERNEL);
	bl = devm_kzalloc(dev, sizeof(*bl), GFP_KERNEL);
	if (!data || !bl)
		return -ENOMEM;
	bl->name = "yuga-lcd";
	bl->max_current = 20200;
	bl->default_brightness = 20;
	bl->pwm = 0;
	data->boost_ovp = LM3533_BOOST_OVP_24V;
	data->boost_freq = LM3533_BOOST_FREQ_500KHZ;
	data->backlights = bl;
	data->num_backlights = 1;
	dev->platform_data = data;
	return 0;
}

static int lm3533_yuga_outputs(struct lm3533 *chip)
{
	int ret;

	if (!lm3533_is_yuga(chip->dev))
		return 0;
	ret = lm3533_set_hvled_config(chip, 1, 0);
	if (ret)
		return ret;
	ret = lm3533_set_hvled_config(chip, 2, 0);
	if (ret)
		return ret;
	/* Bank A linear, no ALS; bank B stays unconfigured/disabled. */
	ret = lm3533_update(chip, 0x1a, 0x02, 0x03);
	if (ret)
		return ret;
	/* PWM high polarity, 24 V OVP, 500 kHz; PWM input itself is disabled. */
	return lm3533_update(chip, LM3533_REG_BOOST_PWM, 0x08, 0x08);
}
